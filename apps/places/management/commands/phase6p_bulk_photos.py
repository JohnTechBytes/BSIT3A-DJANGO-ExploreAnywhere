"""ExploreAnywhere Phase 6P: cross-city Commons discovery and human-reviewed bulk import.

DISCOVER performs read-only database queries and network GETs. It writes only a
separate review CSV/HTML under phase6_photo_review. It does NOT approve photos.

PREVIEW reads reviewer decisions and database records without database writes.

APPLY requires BOTH --apply-approved and --confirm-reviewed and imports ONLY
CSV rows independently approved for identity and rights. Existing covers are
never replaced. Images for different establishments must not be inferred from
similar business names or geospatial proximity alone.

Install in apps/places/management/commands/phase6p_bulk_photos.py.
"""
import csv
import html
import os
import re
import shutil
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.error import HTTPError, URLError

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.places.models import Place
from apps.places.management.commands.phase6o_business_photos import (
    LICENSES, clean_text, error_detail, safe_cell, trusted_https,
)
from apps.places.management.commands.phase6o_search_commons import commons_search

REPORT_DIR = Path(settings.BASE_DIR) / 'phase6_photo_review'
CSV_PATH = REPORT_DIR / 'all_cities_photo_candidates.csv'
GALLERY_PATH = REPORT_DIR / 'all_cities_photo_gallery.html'
COLUMNS = (
    'place_id', 'city_id', 'city_name', 'place_name', 'place_slug',
    'latitude', 'longitude', 'search_query', 'file_title', 'image_url',
    'source_url', 'credit', 'license', 'license_url', 'match_status',
    'review_decision', 'identity_checked', 'rights_checked',
    'review_notes',
)
REVIEW_COLUMNS = ('review_decision', 'identity_checked', 'rights_checked', 'review_notes')
MAX_IMPORT_PER_RUN = 250
LICENSE_PATHS = {
    'CC BY 4.0': '/licenses/by/4.0',
    'CC BY 3.0': '/licenses/by/3.0',
    'CC BY-SA 4.0': '/licenses/by-sa/4.0',
    'CC BY-SA 3.0': '/licenses/by-sa/3.0',
    'CC0 1.0': '/publicdomain/zero/1.0',
}


def load_rows():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or set(COLUMNS) - set(reader.fieldnames):
            raise CommandError('CSV columns do not match Phase 6P. Original file preserved.')
        rows = list(reader)
    known = set()
    for row in rows:
        key = (row['place_id'], row['source_url'])
        if not row['place_id'] or not row['source_url'] or key in known:
            raise CommandError('CSV contains a malformed/duplicate candidate. Nothing changed.')
        known.add(key)
    return rows


def save_rows(rows):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix('.csv.tmp')
    with tmp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({k: safe_cell(row.get(k, '')) for k in COLUMNS})
    os.replace(tmp, CSV_PATH)


def make_gallery(rows):
    doc = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>ExploreAnywhere — Phase 6P Photo Candidate Review</title>',
        '<style>body{font:15px system-ui;background:#f3f6fb;color:#1a2c45;',
        'margin:0 auto;max-width:1320px;padding:26px}.grid{display:grid;',
        'grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}',
        'article{background:#fff;border:1px solid #d7dfea;border-radius:12px;',
        'overflow:hidden}article img{height:185px;width:100%;object-fit:cover;',
        'background:#e9edf2}article .body{padding:14px}p{overflow-wrap:anywhere}',
        'a{color:#0b57b5}small{color:#536681}</style></head><body>',
        '<h1>All-city Commons photo candidate review</h1>',
        '<p><strong>Every candidate is UNVERIFIED until reviewed.</strong> A photo ',
        'must depict the exact place or business. The Commons description, ',
        'location evidence, creator and license must be checked before marking ',
        '<code>approve / yes / yes</code> in the CSV. Review notes are required.',
        ' Similar brand names and nearby places are not identity evidence.</p>',
        '<main class="grid">',
    ]
    for row in rows:
        if not trusted_https(row.get('image_url'), {'upload.wikimedia.org'}):
            continue
        if not trusted_https(row.get('source_url'), {'commons.wikimedia.org'}):
            continue
        escape = lambda k: html.escape(str(row.get(k) or ''), quote=True)
        doc.append(
            '<article><img loading="lazy" alt="Unverified photo candidate" '
            f'src="{escape("image_url")}"><div class="body">'
            f'<h3>{escape("place_name")}</h3>'
            f'<small>{escape("city_name")} · Place ID {escape("place_id")}</small>'
            f'<p>{escape("file_title")}</p>'
            f'<p>{escape("credit")} · {escape("license")}</p>'
            f'<p><small>{escape("match_status")}</small></p>'
            f'<p><a href="{escape("source_url")}" target="_blank" rel="noopener noreferrer">'
            'Check the original Commons file</a></p>'
            f'<p><small>Review: {escape("review_decision") or "pending"}</small></p>'
            '</div></article>'
        )
    doc.append('</main></body></html>')
    GALLERY_PATH.write_text(''.join(doc), encoding='utf-8')


def discovery_queries(place):
    name = re.sub(r'\s+', ' ', str(place.title or '')).replace('"', '').strip()[:100]
    city = re.sub(r'\s+', ' ', str(place.city.name or '')).replace('"', '').strip()[:80]
    if not name or not city:
        return ()
    # Broadening only affects *leads*, never approval decisions.
    terms = [f'"{name}" "{city}"']
    if city.casefold() == 'kabankalan':
        terms.append(f'"{name}" "Negros Occidental"')
    else:
        terms.append(f'"{name}" "{city}" Philippines')
    return tuple(dict.fromkeys(terms))


def candidate_errors(row, place):
    errs = []
    if place is None:
        return ['Place ID does not exist']
    if str(place.pk) != row.get('place_id'):
        errs.append('Place ID changed')
    if str(place.city_id) != row.get('city_id'):
        errs.append('City ID changed')
    if str(place.slug) != row.get('place_slug'):
        errs.append('Place slug changed')
    if place.cover_image or place.cover_image_url:
        errs.append('Existing cover already present: never overwrite')
    if str(row.get('review_decision', '')).strip().lower() != 'approve':
        errs.append('Not explicitly approved')
    if str(row.get('identity_checked', '')).strip().lower() != 'yes':
        errs.append('Identity not confirmed')
    if str(row.get('rights_checked', '')).strip().lower() != 'yes':
        errs.append('Rights not confirmed')
    if len(str(row.get('review_notes', '')).strip()) < 20:
        errs.append('Review notes must explain identity and license evidence (20+ characters)')
    if str(row.get('license', '')).strip() not in LICENSES:
        errs.append('Unsupported license')
    if not clean_text(row.get('credit')):
        errs.append('Missing creator credit')
    if not trusted_https(row.get('image_url'), {'upload.wikimedia.org'}):
        errs.append('Image is not a trusted Commons-hosted HTTPS URL')
    if not trusted_https(row.get('source_url'), {'commons.wikimedia.org'}):
        errs.append('Missing trusted Commons file source')
    if not trusted_https(row.get('license_url'), {'creativecommons.org'}):
        errs.append('Missing trusted license URL')
    else:
        expected_license_path = LICENSE_PATHS.get(str(row.get('license', '')).strip())
        actual_license_path = urlsplit(row['license_url']).path.rstrip('/')
        if not expected_license_path or actual_license_path != expected_license_path:
            errs.append('License URL does not match declared license')
    # Source page should identify the exact Commons file selected for review.
    filename = str(row.get('file_title', '')).removeprefix('File:').replace('_', ' ').strip().casefold()
    source_file = unquote(urlsplit(str(row.get('source_url', ''))).path.rsplit('/', 1)[-1])
    source_file = source_file.removeprefix('File:').replace('_', ' ').strip().casefold()
    if not filename or not source_file or filename != source_file:
        errs.append('Commons source does not correspond to selected file title')
    for name, value in (
        ('cover_image_url', row.get('image_url', '')),
        ('photo_credit', clean_text(row.get('credit'), 500)),
        ('photo_source_url', row.get('source_url', '')),
        ('photo_license', row.get('license', '')),
        ('photo_license_url', row.get('license_url', '')),
    ):
        maximum = Place._meta.get_field(name).max_length
        if maximum and len(str(value)) > maximum:
            errs.append(f'{name} exceeds model length')
    return errs


def audited_approvals(rows, city_id):
    approved = [r for r in rows if str(r.get('review_decision', '')).strip().lower() == 'approve'
                and (city_id is None or r.get('city_id') == str(city_id))]
    if len(approved) > MAX_IMPORT_PER_RUN:
        raise CommandError(f'Over {MAX_IMPORT_PER_RUN} approved photos; import one city at a time using --city-id.')
    counts = {}
    image_uses = {}
    for r in approved:
        counts[r['place_id']] = counts.get(r['place_id'], 0) + 1
        image_uses.setdefault(r.get('source_url', ''), set()).add(r['place_id'])
    places = Place.objects.filter(pk__in=[int(r['place_id']) for r in approved if r['place_id'].isdigit()]).in_bulk()
    accepted, rejected = [], []
    for r in approved:
        problems = candidate_errors(r, places.get(int(r['place_id'])) if r['place_id'].isdigit() else None)
        if counts[r['place_id']] != 1:
            problems.append('Multiple approved photos for this place')
        if len(image_uses.get(r.get('source_url', ''), ())) > 1:
            problems.append('One Commons file approved for multiple distinct places')
        if problems:
            rejected.append((r, problems))
        else:
            accepted.append(r)
    return approved, accepted, rejected


class Command(BaseCommand):
    help = 'Phase 6P: discover unverified Commons candidates across cities; import only individually reviewed photos.'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--discover', action='store_true', help='Find Commons leads; database read-only')
        group.add_argument('--preview-approved', action='store_true', help='Validate approved candidates; database read-only')
        group.add_argument('--apply-approved', action='store_true', help='Import individually approved photographs (requires confirmation)')
        parser.add_argument('--confirm-reviewed', action='store_true', help='Explicit opt-in to DB writes with --apply-approved')
        parser.add_argument('--city-id', type=int, help='Restrict to the given city ID; omit for all cities')
        parser.add_argument('--limit', type=int, default=20, help='Number of missing-cover places to search per batch (1–30)')
        parser.add_argument('--offset', type=int, default=0, help='Skip this number of sorted eligible places')
        parser.add_argument('--per-query', type=int, default=3, help='Max Commons leads per query (1–5)')
        parser.add_argument('--rescan', action='store_true', help='Re-query places with existing leads; keep prior reviewer work')

    def handle(self, *args, **opts):
        if not 1 <= opts['limit'] <= 30 or opts['offset'] < 0 or not 1 <= opts['per_query'] <= 5:
            raise CommandError('Use --limit 1–30, --offset >= 0, --per-query 1–5.')
        if opts['city_id'] is not None and opts['city_id'] < 1:
            raise CommandError('--city-id must be a positive number')
        if opts['confirm_reviewed'] and not opts['apply_approved']:
            raise CommandError('--confirm-reviewed is only valid with --apply-approved')
        if opts['apply_approved'] and not opts['confirm_reviewed']:
            raise CommandError('Import refused: --apply-approved also requires --confirm-reviewed')
        if opts['rescan'] and not opts['discover']:
            raise CommandError('--rescan only works with --discover')
        rows = load_rows()
        if opts['discover']:
            self.discover(rows, opts)
        else:
            self.import_preview_or_apply(rows, opts)

    def discover(self, rows, opts):
        agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
        if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT to app name and your real contact email.')
        places = Place.objects.select_related('city').order_by('city_id', 'id')
        if opts['city_id'] is not None:
            places = places.filter(city_id=opts['city_id'])
        # Page across the *full* inventory, so offsets remain stable even if
        # photographs are imported between separate discovery batches.
        all_places = list(places)
        missing_count = sum(not p.cover_image and not p.cover_image_url for p in all_places)
        targets = [p for p in all_places[opts['offset']:opts['offset'] + opts['limit']]
                   if not p.cover_image and not p.cover_image_url]
        seen = {(r['place_id'], r['source_url']) for r in rows}
        known_ids = {r['place_id'] for r in rows}
        scanned = 0
        added = 0
        errors = 0
        backup_created = False
        self.stdout.write(f'DISCOVERY: {len(targets)} missing-cover places in inventory window '
                          f'{opts["offset"]}–{opts["offset"] + opts["limit"] - 1} of {len(all_places)}; '
                          f'{missing_count} total missing covers. All leads UNVERIFIED. No MySQL writes.')
        for n, place in enumerate(targets, 1):
            if not opts['rescan'] and str(place.pk) in known_ids:
                self.stdout.write(f'[{n}/{len(targets)}] SKIP {place.title}: prior leads retained')
                continue
            queries = discovery_queries(place)
            if not queries:
                continue
            scanned += 1
            self.stdout.write(f'[{n}/{len(targets)}] SEARCH {place.city.name}: {place.title} ({place.pk})')
            for query in queries:
                try:
                    candidates = commons_search(query, agent, opts['per_query'])
                except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                    errors += 1
                    self.stdout.write(f'  ERROR {query!r}: {error_detail(exc)}')
                    time.sleep(0.8)
                    continue
                for candidate in candidates:
                    key = (str(place.pk), candidate['source_url'])
                    if key in seen:
                        continue
                    seen.add(key)
                    row = {
                        'place_id': str(place.pk),
                        'city_id': str(place.city_id),
                        'city_name': safe_cell(place.city.name),
                        'place_name': safe_cell(place.title),
                        'place_slug': place.slug,
                        'latitude': str(getattr(place, 'latitude', '') or ''),
                        'longitude': str(getattr(place, 'longitude', '') or ''),
                        'search_query': query,
                        **candidate,
                        **{col: '' for col in REVIEW_COLUMNS},
                    }
                    rows.append(row)
                    added += 1
                self.stdout.write(f'  {query!r}: {len(candidates)} leads')
                if added and not backup_created and CSV_PATH.exists():
                    backup = CSV_PATH.with_name(CSV_PATH.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
                    shutil.copy2(CSV_PATH, backup)
                    backup_created = True
                    self.stdout.write(f'  Reviewer CSV backup: {backup}')
                if added:
                    save_rows(rows)
                time.sleep(0.8)
        if not CSV_PATH.exists():
            save_rows(rows)
        make_gallery(rows)
        self.stdout.write(self.style.SUCCESS(
            f'DISCOVERY DONE: places searched={scanned}, new unverified candidates={added}, '
            f'errors={errors}, retained candidates={len(rows)}. Database unchanged.'))
        self.stdout.write(f'CSV: {CSV_PATH}\nGALLERY: {GALLERY_PATH}')
        self.stdout.write('NEXT: review Commons identity and licensing. DO NOT mark a lead approve without evidence.')

    def import_preview_or_apply(self, rows, opts):
        if not CSV_PATH.exists():
            raise CommandError('No review CSV yet. Run --discover and verify individual candidates first.')
        approved, accepted, rejected = audited_approvals(rows, opts['city_id'])
        self.stdout.write(f'BULK REVIEW: {len(approved)} approved, {len(accepted)} eligible, '
                          f'{len(rejected)} blocked.')
        for r, reasons in rejected[:25]:
            self.stdout.write(f'  BLOCKED {r["place_id"]}: {r["place_name"]} — {"; ".join(reasons)}')
        for r in accepted[:25]:
            self.stdout.write(f'  READY {r["place_id"]}: {r["place_name"]} ({r["city_name"]})')
        if opts['preview_approved']:
            self.stdout.write(self.style.WARNING('PREVIEW ONLY: database unchanged.'))
            return
        # Fail the entire batch on ANY rejected approval: never silently partially import.
        if rejected:
            raise CommandError('Import refused: one or more approved records are blocked. Fix reviews or revoke approval.')
        if not accepted:
            self.stdout.write('NOTHING TO APPLY. Database unchanged.')
            return
        # Lock the existing Place rows and re-evaluate eligibility against their latest values.
        with transaction.atomic():
            ids = [int(r['place_id']) for r in accepted]
            locked = {p.pk: p for p in Place.objects.select_for_update().filter(pk__in=ids)}
            for r in accepted:
                current_errors = candidate_errors(r, locked.get(int(r['place_id'])))
                if current_errors:
                    raise CommandError(f'Import cancelled: Place {r["place_id"]} changed: '
                                       + '; '.join(current_errors))
            for r in accepted:
                changed = (Place.objects.filter(pk=int(r['place_id']),
                                                city_id=int(r['city_id']),
                                                slug=r['place_slug'])
                           .filter(Q(cover_image='') | Q(cover_image__isnull=True))
                           .filter(Q(cover_image_url='') | Q(cover_image_url__isnull=True))
                           .update(cover_image_url=r['image_url'].strip(),
                                   photo_credit=clean_text(r['credit'], 500),
                                   photo_source_url=r['source_url'].strip(),
                                   photo_license=r['license'].strip(),
                                   photo_license_url=r['license_url'].strip()))
                if changed != 1:
                    raise CommandError('Unexpected concurrent update; entire transaction rolled back.')
        self.stdout.write(self.style.SUCCESS(
            f'APPLIED: exactly {len(accepted)} independently approved covers. '
            'Publication/verification fields untouched; existing covers preserved.'))
