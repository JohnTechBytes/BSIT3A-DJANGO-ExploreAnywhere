"""Phase 6O: conservative, human-reviewed Kabankalan Wikimedia photo collection.

All network operations are READ ONLY and only request exact OSM IDs and Commons files.
NO place can be verified or published by this command.
"""
import csv
import html
import json
import os
import re
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, unquote, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.html import strip_tags

from apps.places.models import Place

CITY_ID = 2
SLUG_RE = re.compile(r'^osm-(node|way|relation)-(\d+)$')
QID_RE = re.compile(r'^Q[1-9]\d*$')
LICENSES = {'CC BY 4.0', 'CC BY 3.0', 'CC BY-SA 4.0', 'CC BY-SA 3.0', 'CC0 1.0'}
COLUMNS = (
    'place_id', 'place_name', 'place_slug', 'publication', 'already_has_cover',
    'osm_url', 'candidate_method', 'image_url', 'source_url', 'credit',
    'license', 'license_url', 'match_status', 'lookup_note',
    'review_decision', 'identity_checked', 'rights_checked', 'review_notes',
)
REVIEW_DIR = Path(settings.BASE_DIR) / 'phase6_photo_review'
CSV_FILE = REVIEW_DIR / 'kabankalan_photo_review.csv'
HTML_FILE = REVIEW_DIR / 'kabankalan_photo_gallery.html'


def trusted_https(value, hosts):
    try:
        parsed = urlsplit(str(value or '').strip())
        return (parsed.scheme == 'https' and parsed.hostname in hosts and not parsed.username
                and not parsed.password and not parsed.fragment and parsed.port in (None, 443))
    except (ValueError, TypeError):
        return False


def safe_cell(value):
    text = str(value or '')
    # Prevent spreadsheet formula injection when the CSV is opened in Excel.
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r')) else text


def clean_text(value, max_length=500):
    return re.sub(r'\s+', ' ', html.unescape(strip_tags(str(value or '')))).strip()[:max_length]


def network_json(url, agent):
    if not trusted_https(url, {'api.openstreetmap.org', 'www.wikidata.org', 'commons.wikimedia.org'}):
        raise ValueError('Unexpected API URL')
    req = Request(url, headers={'User-Agent': agent, 'Accept': 'application/json'})
    with urlopen(req, timeout=22, context=ssl.create_default_context()) as response:
        payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError('API response too large')
        return json.loads(payload)


def osm_tags(slug, agent):
    match = SLUG_RE.fullmatch(slug)
    if not match:
        return {}
    kind, identifier = match.groups()
    url = f'https://api.openstreetmap.org/api/0.6/{kind}/{identifier}.json'
    data = network_json(url, agent)
    for element in data.get('elements', []):
        if element.get('type') == kind and str(element.get('id')) == identifier:
            return element.get('tags') or {}
    return {}


def commons_filename(tags, agent):
    # Only exact OSM Commons-file or Wikidata P18 connections; no name-based image searches.
    for tag in ('wikimedia_commons', 'image'):
        candidate = str(tags.get(tag) or '').strip()
        if candidate.startswith('File:') and len(candidate) <= 300:
            return candidate[5:], f'OSM {tag} File tag'
        if candidate.startswith('https://commons.wikimedia.org/wiki/File:'):
            filename = unquote(candidate.split('/wiki/File:', 1)[1]).replace('_', ' ')
            if filename and len(filename) <= 300:
                return filename, f'OSM {tag} Commons link'
    qid = str(tags.get('wikidata') or '').strip()
    if not QID_RE.fullmatch(qid):
        return '', 'No direct Commons file or Wikidata ID in OSM'
    data = network_json('https://www.wikidata.org/wiki/Special:EntityData/' + qid + '.json', agent)
    entity = data.get('entities', {}).get(qid, {})
    for claim in entity.get('claims', {}).get('P18', []):
        value = claim.get('mainsnak', {}).get('datavalue', {}).get('value')
        if isinstance(value, str) and value.strip() and len(value) <= 300:
            return value.strip(), f'Wikidata {qid} P18 (linked from exact OSM ID)'
    return '', f'Wikidata {qid} has no P18 image'


def commons_metadata(filename, agent):
    if not filename or len(filename) > 300 or any(c in filename for c in '\r\n\0'):
        return None
    params = urlencode({'action': 'query', 'format': 'json', 'titles': 'File:' + filename,
                        'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 960})
    response = network_json('https://commons.wikimedia.org/w/api.php?' + params, agent)
    for page in response.get('query', {}).get('pages', {}).values():
        for info in page.get('imageinfo', []):
            if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                continue
            ext = info.get('extmetadata') or {}
            def met(key):
                return str((ext.get(key) or {}).get('value') or '')
            author = clean_text(met('Artist') or met('Attribution'), 500)
            result = {
                'image_url': info.get('thumburl') or info.get('url') or '',
                'source_url': info.get('descriptionurl') or '',
                'credit': author,
                'license': clean_text(met('LicenseShortName'), 100),
                'license_url': met('LicenseUrl').strip(),
            }
            if not trusted_https(result['image_url'], {'upload.wikimedia.org'}):
                return None
            if not trusted_https(result['source_url'], {'commons.wikimedia.org'}):
                return None
            return result
    return None


def inventory():
    rows = []
    fields = ('id', 'title', 'slug', 'is_verified', 'is_active', 'cover_image', 'cover_image_url')
    for place in Place.objects.filter(city_id=CITY_ID).order_by('id').values(*fields):
        match = SLUG_RE.fullmatch(place['slug'] or '')
        present = bool(place['cover_image'] or place['cover_image_url'])
        rows.append({
            'place_id': str(place['id']), 'place_name': safe_cell(place['title']),
            'place_slug': place['slug'] or '',
            'publication': ('published' if place['is_active'] and place['is_verified']
                            else 'not published'),
            'already_has_cover': 'yes' if present else 'no',
            'osm_url': f'https://www.openstreetmap.org/{match.group(1)}/{match.group(2)}' if match else '',
            'candidate_method': '', 'image_url': '', 'source_url': '', 'credit': '',
            'license': '', 'license_url': '',
            'match_status': 'existing cover — preserved' if present else 'not checked',
            'lookup_note': '', 'review_decision': '', 'identity_checked': '',
            'rights_checked': '', 'review_notes': '',
        })
    return rows


def load_csv():
    if not CSV_FILE.exists():
        return None
    with CSV_FILE.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        if set(COLUMNS) - set(reader.fieldnames or []):
            raise CommandError('Existing CSV has missing columns; refusing to overwrite reviewer work.')
        data = list(reader)
    seen = set()
    for row in data:
        if row['place_id'] in seen:
            raise CommandError('Duplicate place_id in CSV; refusing to continue.')
        seen.add(row['place_id'])
    return data


def save_csv(rows):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CSV_FILE.with_suffix('.csv.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, CSV_FILE)


def html_gallery(rows):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    parts = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width, initial-scale=1">',
             '<title>ExploreAnywhere | Phase 6O Photo Review</title>',
             '<style>body{font:15px system-ui,sans-serif;max-width:1350px;margin:auto;padding:24px;',
             'background:#f5f7fb;color:#182b42}header{margin-bottom:24px}.grid{display:grid;',
             'grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}',
             'article{border:1px solid #dbe4ef;border-radius:12px;background:white;overflow:hidden}',
             'article img{width:100%;height:180px;object-fit:cover;background:#eef0f4}',
             'article .body{padding:14px}h2{font-size:17px;margin:0 0 8px}',
             'p{overflow-wrap:anywhere}a{color:#1253b5}small{color:#4d627b}',
             '</style></head><body><header><h1>Kabankalan photo candidate review</h1>',
             '<p>Candidate images are NOT proof of a correct place match. Open the original Wikimedia Commons ',
             'source and confirm the photo depicts the correct business or destination before approving ',
             'the corresponding CSV row. Check the license and credits. This is a read-only HTML gallery.</p>',
             '</header><main class="grid">']
    count = 0
    for row in rows:
        if not row.get('image_url'):
            continue
        image_url = row['image_url']
        if not trusted_https(image_url, {'upload.wikimedia.org'}):
            continue
        count += 1
        esc = lambda key: html.escape(str(row.get(key) or ''), quote=True)
        source = row.get('source_url') or ''
        link = (f'<a href="{html.escape(source, quote=True)}" target="_blank" rel="noopener noreferrer">'
                'Open Commons source</a>') if trusted_https(source, {'commons.wikimedia.org'}) else ''
        parts.append(f'<article><img loading="lazy" alt="Unverified candidate for {esc("place_name")}" '
                     f'src="{esc("image_url")}"><div class="body"><h2>{esc("place_name")}</h2>'
                     f'<small>ID {esc("place_id")} · {esc("publication")}</small>'
                     f'<p>{esc("candidate_method")}</p><p>{esc("license")} · {esc("credit")}</p>'
                     f'<p>{link}</p><small>Review decision: {esc("review_decision") or "not reviewed"}</small>'
                     '</div></article>')
    parts += ['</main>', f'<p>{count} photo candidates shown. Original files were not downloaded.</p>', '</body></html>']
    HTML_FILE.write_text(''.join(parts), encoding='utf-8')
    return count


def eligible(row, place):
    errors = []
    if place is None or place.city_id != CITY_ID or str(place.pk) != (row.get('place_id') or ''):
        return ['Place ID is missing or not Kabankalan']
    if (row.get('place_slug') or '') != place.slug:
        errors.append('Place slug changed; manual investigation needed')
    if place.cover_image or place.cover_image_url:
        errors.append('Existing image will never be overwritten')
    if (row.get('review_decision') or '').strip().lower() != 'approve':
        errors.append('Not explicitly approved')
    if (row.get('identity_checked') or '').strip().lower() != 'yes':
        errors.append('Photo identity not independently confirmed')
    if (row.get('rights_checked') or '').strip().lower() != 'yes':
        errors.append('License and attribution not confirmed')
    if not (row.get('review_notes') or '').strip():
        errors.append('Reviewer evidence/notes required')
    if (row.get('license') or '').strip() not in LICENSES:
        errors.append('Unsupported license')
    if not clean_text(row.get('credit')):
        errors.append('Missing creator credit')
    if not trusted_https(row.get('image_url'), {'upload.wikimedia.org'}):
        errors.append('Invalid Commons-hosted image')
    if not trusted_https(row.get('source_url'), {'commons.wikimedia.org'}):
        errors.append('Invalid Commons source')
    if not trusted_https(row.get('license_url'), {'creativecommons.org'}):
        errors.append('Invalid Creative Commons license URL')
    for field, csv_key in [('cover_image_url', 'image_url'), ('photo_credit', 'credit'),
                           ('photo_source_url', 'source_url'), ('photo_license', 'license'),
                           ('photo_license_url', 'license_url')]:
        maximum = Place._meta.get_field(field).max_length
        if maximum and len(clean_text(row.get(csv_key), 9999)) > maximum:
            errors.append(field + ' exceeds model max length')
    return errors


class Command(BaseCommand):
    help = 'Generate and review authentic Commons photo candidates for Kabankalan without publishing businesses.'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--inventory', action='store_true', help='Offline CSV inventory; no network or DB writes')
        group.add_argument('--collect', action='store_true', help='Look up exact OSM IDs and Wikimedia Commons candidate images')
        group.add_argument('--apply-approved', action='store_true', help='Preview/apply explicitly approved photo metadata')
        parser.add_argument('--limit', type=int, default=25, help='Collect at most 1–50 selected rows')
        parser.add_argument('--offset', type=int, default=0, help='Start offset for collection')
        parser.add_argument('--all', action='store_true', help='Collect all missing-cover OSM rows (may take several minutes)')
        parser.add_argument('--dry-run', action='store_true', help='Never modify database')
        parser.add_argument('--confirm-reviewed', action='store_true', help='Commit reviewed and eligible rows to database')

    def handle(self, *args, **opts):
        if opts['offset'] < 0 or not 1 <= opts['limit'] <= 50:
            raise CommandError('--offset must be >= 0 and --limit must be 1–50')
        if opts['confirm_reviewed'] and not opts['apply_approved']:
            raise CommandError('--confirm-reviewed is only for --apply-approved')
        # Guard against accidentally running this command on the wrong city/database.
        from apps.cities.models import City
        city = City.objects.filter(pk=CITY_ID).first()
        if city is None or city.name.strip().casefold() != 'kabankalan':
            raise CommandError('City 2 is not Kabankalan in this database. No action taken.')
        existing = load_csv()
        latest = inventory()
        if existing is None:
            rows = latest
        else:
            previous = {r['place_id']: r for r in existing}
            rows = []
            for fresh in latest:
                old = previous.get(fresh['place_id'])
                if old and old.get('place_slug') == fresh['place_slug']:
                    fresh.update({k: old.get(k, '') for k in COLUMNS if k not in
                                 ('place_id', 'place_name', 'place_slug', 'publication', 'already_has_cover', 'osm_url')})
                rows.append(fresh)
        if opts['inventory']:
            save_csv(rows)
            images = html_gallery(rows)
            missing = sum(r['already_has_cover'] == 'no' for r in rows)
            self.stdout.write(self.style.SUCCESS(f'INVENTORY OK: {len(rows)} Kabankalan places; {missing} without cover. Database unchanged.'))
            self.stdout.write(f'CSV: {CSV_FILE}\nGALLERY: {HTML_FILE} ({images} candidates)')
            return
        if opts['collect']:
            agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
            if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
                raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT with application name and your real contact email.')
            if existing is None:
                save_csv(rows)
            targets = [r for r in rows if r['already_has_cover'] == 'no' and SLUG_RE.fullmatch(r['place_slug'])]
            selected = targets if opts['all'] else targets[opts['offset']:opts['offset'] + opts['limit']]
            if len(selected) > 300:
                raise CommandError('Refusing more than 300 OSM requests.')
            counts = {'found': 0, 'no_photo': 0, 'error': 0, 'preserved': 0}
            self.stdout.write(f'Collecting {len(selected)} exact-OSM photo leads from {len(targets)} eligible places. NO DATABASE WRITES.')
            for index, row in enumerate(selected, start=1):
                if (row.get('review_decision') or '').strip() or row.get('image_url'):
                    counts['preserved'] += 1
                    continue
                try:
                    tags = osm_tags(row['place_slug'], agent)
                    filename, method = commons_filename(tags, agent)
                    row['candidate_method'] = method
                    if filename:
                        metadata = commons_metadata(filename, agent)
                        if metadata:
                            row.update(metadata)
                            row['match_status'] = 'photo found — human review required'
                            if metadata['license'] not in LICENSES or not metadata['credit']:
                                row['match_status'] = 'photo found — license/credit needs review'
                            counts['found'] += 1
                        else:
                            row['match_status'] = 'no supported Commons image metadata'
                            counts['no_photo'] += 1
                    else:
                        row['match_status'] = 'no exact linked Commons image'
                        counts['no_photo'] += 1
                    row['lookup_note'] = ''
                except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
                    row['match_status'] = 'lookup error — retry later'
                    row['lookup_note'] = clean_text(type(exc).__name__ + ': ' + str(exc), 200)
                    counts['error'] += 1
                save_csv(rows)  # Preserve each completed lookup before the next request.
                self.stdout.write(f'[{index}/{len(selected)}] {row["place_name"]}: {row["match_status"]}')
                if index < len(selected):
                    time.sleep(0.8)  # Be considerate of volunteer-run data services.
            images = html_gallery(rows)
            self.stdout.write(self.style.SUCCESS(f'COLLECTION DONE: {counts}. Candidate gallery: {images} photos. Database unchanged.'))
            self.stdout.write(f'CSV: {CSV_FILE}\nGALLERY: {HTML_FILE}')
            return
        # Explicit-review importer, read-only unless --confirm-reviewed.
        approved = [r for r in rows if (r.get('review_decision') or '').strip().lower() == 'approve']
        places = Place.objects.filter(city_id=CITY_ID, id__in=[r['place_id'] for r in approved]).in_bulk()
        accepted, declined = [], []
        for row in approved:
            try:
                identifier = int(row['place_id'])
            except (ValueError, TypeError):
                declined.append((row['place_name'], ['Malformed place ID']))
                continue
            place = places.get(identifier)
            problems = eligible(row, place)
            if problems:
                declined.append((row['place_name'], problems))
            else:
                accepted.append(row)
        self.stdout.write(f'APPROVAL PREVIEW: {len(approved)} marked approve, {len(accepted)} eligible, {len(declined)} blocked.')
        for name, reasons in declined[:20]:
            self.stdout.write('  BLOCKED: ' + name + ' — ' + '; '.join(reasons))
        if not opts['confirm_reviewed'] or opts['dry_run']:
            self.stdout.write(self.style.WARNING('PREVIEW ONLY: database unchanged. To apply, use --apply-approved --confirm-reviewed'))
            return
        changed = 0
        with transaction.atomic():
            for row in accepted:
                changed += (Place.objects.filter(pk=int(row['place_id']), city_id=CITY_ID, slug=row['place_slug'])
                            .filter(Q(cover_image='') | Q(cover_image__isnull=True))
                            .filter(Q(cover_image_url='') | Q(cover_image_url__isnull=True))
                            .update(cover_image_url=row['image_url'].strip(),
                                    photo_credit=clean_text(row['credit'], 500),
                                    photo_source_url=row['source_url'].strip(),
                                    photo_license=row['license'].strip(),
                                    photo_license_url=row['license_url'].strip()))
        self.stdout.write(self.style.SUCCESS(f'APPLIED: {changed} approved photo covers. No publication/verification fields changed.'))
