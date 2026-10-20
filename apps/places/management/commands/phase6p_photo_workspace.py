"""ExploreAnywhere Phase 6P.5 — Kabankalan-only photo review workspace.

Adds a unified, static HTML dashboard for ONLINE Commons candidates and LOCAL
owner-authorized photographs. It NEVER writes MySQL or auto-approves anything.

Commands:
  --status         Summarize local and online reviews (read-only)
  --scan-local     Create image checksum / exact-place-ID manifest (no DB writes)
  --prepare-local  Fill only blank file_name and file_sha256 CSV cells for files
                   named PLACEID__description.jpg; preserve all approvals and
                   other reviewer fields. Makes a timestamped CSV backup.
  --dashboard      Create a Kabankalan-only combined HTML dashboard.

Import remains exclusively through existing review-gated Phase 6P commands.
"""
import csv
import hashlib
import html
import os
import re
import shutil
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from django.core.management.base import BaseCommand, CommandError
from apps.cities.models import City
from apps.places.models import Place
from apps.places.management.commands import phase6p_bulk_photos as online
from apps.places.management.commands import phase6p_local_photo_intake as local

CITY_ID = 2
MANIFEST = local.REVIEW / 'kabankalan_local_staging_manifest.csv'
DASHBOARD = local.REVIEW / 'kabankalan_photo_workspace.html'
MANIFEST_COLUMNS = (
    'file_name', 'place_id', 'place_name', 'sha256', 'size_bytes', 'status', 'note'
)
NAME_ID = re.compile(r'^([1-9][0-9]*)__([A-Za-z0-9][A-Za-z0-9._ -]*)\.(jpg|jpeg|png|webp)$', re.I)


def ensure_city():
    city = City.objects.filter(pk=CITY_ID).first()
    if not city or city.name.strip().casefold() != 'kabankalan':
        raise CommandError('City ID 2 is not Kabankalan. Nothing changed.')


def get_places():
    return {p.pk: p for p in Place.objects.filter(city_id=CITY_ID).order_by('pk')}


def online_rows():
    # The existing CSV is shared with other cities, so filter every use here.
    return [r for r in online.load_rows() if r.get('city_id') == str(CITY_ID)]


def local_rows():
    return local.read_rows() if local.CSV_PATH.exists() else []


def file_hash(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def scan(places, reviews):
    """Return (manifest, eligible) without modifying any Place or reviewer row."""
    previous = {int(r['place_id']): r for r in reviews}
    result = []
    files = sorted((f for f in local.STAGING.iterdir() if f.is_file() or f.is_symlink()),
                   key=lambda p: p.name.casefold()) if local.STAGING.exists() else []
    for f in files:
        name = f.name
        row = dict.fromkeys(MANIFEST_COLUMNS, '')
        row['file_name'] = name
        match = NAME_ID.fullmatch(name)
        if not match or not local.safe_name(name):
            row['status'] = 'manual_rename_needed'
            row['note'] = 'Rename using PLACEID__description.jpg; no automatic name matching'
        else:
            place_id = int(match.group(1))
            row['place_id'] = str(place_id)
            place = places.get(place_id)
            if place is None:
                row['status'] = 'not_kabankalan_place_id'
            else:
                row['place_name'] = place.title
                if place.cover_image or place.cover_image_url:
                    row['status'] = 'existing_cover_preserved'
                elif f.is_symlink():
                    row['status'] = 'symlink_refused'
                else:
                    try:
                        size = f.stat().st_size
                        row['size_bytes'] = str(size)
                        if size < 100 or size > local.MAX_FILE_BYTES:
                            raise ValueError('File size outside 100 bytes–15 MB')
                        row['sha256'] = file_hash(f)
                        # Reuse strict byte, file-size and Pillow verification.
                        local.verified_file({'file_name': name, 'file_sha256': row['sha256']})
                    except (ValueError, OSError) as exc:
                        row['status'] = 'invalid_image'
                        row['note'] = str(exc)[:200]
                    else:
                        previous_row = previous.get(place_id)
                        if not previous_row:
                            row['status'] = 'missing_review_inventory'
                            row['note'] = 'Run phase6p_local_photo_intake --inventory'
                        elif previous_row.get('place_slug') != place.slug or previous_row.get('place_name') != place.title:
                            row['status'] = 'place_identity_changed'
                        elif previous_row.get('file_name') and previous_row['file_name'] != name:
                            row['status'] = 'review_already_has_other_photo'
                        elif previous_row.get('file_name') == name:
                            row['status'] = 'already_staged_in_review'
                        elif (previous_row.get('review_decision') or '').strip():
                            row['status'] = 'review_decision_preserved'
                        else:
                            row['status'] = 'ready_for_csv_staging'
        result.append(row)

    # Two files for the same place or identical bytes across places are NOT
    # safe to automatically associate/submit; require manual resolution.
    place_counts = Counter(r['place_id'] for r in result if r['status'] == 'ready_for_csv_staging')
    hashes = defaultdict(set)
    for r in result:
        if r['status'] == 'ready_for_csv_staging' and r['sha256']:
            hashes[r['sha256']].add(r['place_id'])
    for r in result:
        if r['status'] != 'ready_for_csv_staging':
            continue
        if place_counts[r['place_id']] > 1:
            r['status'] = 'multiple_photos_same_place'
            r['note'] = 'Choose one photograph and leave the others outside staging'
        elif len(hashes[r['sha256']]) > 1:
            r['status'] = 'same_photo_for_multiple_places'
            r['note'] = 'Do not use the same photograph to depict different places'
    return result


def export_manifest(rows):
    local.REVIEW.mkdir(parents=True, exist_ok=True)
    temp = MANIFEST.with_name(MANIFEST.name + '.tmp')
    with temp.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=MANIFEST_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: online.safe_cell(row.get(k, '')) for k in MANIFEST_COLUMNS})
    os.replace(temp, MANIFEST)


def escape(value):
    return html.escape(str(value or ''), quote=True)


def render_dashboard(places, internet, reviews, manifest):
    internet_by_id = defaultdict(list)
    for r in internet:
        if r.get('place_id', '').isascii() and r['place_id'].isdecimal():
            internet_by_id[int(r['place_id'])].append(r)
    review_by_id = {int(r['place_id']): r for r in reviews}
    files_by_id = defaultdict(list)
    for r in manifest:
        if r.get('place_id', '').isascii() and r['place_id'].isdecimal():
            files_by_id[int(r['place_id'])].append(r)
    covered = sum(bool(p.cover_image or p.cover_image_url) for p in places.values())
    pub_missing = sum(p.is_active and p.is_verified and not (p.cover_image or p.cover_image_url)
                      for p in places.values())
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>ExploreAnywhere | Kabankalan Photo Workspace</title>',
        '<style>body{font:15px system-ui,sans-serif;background:#f6f8fc;color:#213247;',
        'margin:0 auto;max-width:1320px;padding:22px}h1{margin-bottom:8px}',
        '.note{color:#52657d}.metrics{display:flex;flex-wrap:wrap;gap:12px;margin:22px 0}',
        '.metric{background:white;border:1px solid #dce4f0;border-radius:12px;padding:16px;',
        'flex:1;min-width:150px}.metric b{display:block;font-size:24px}',
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(290px,1fr));gap:14px}',
        'article{background:white;border:1px solid #dce4f0;border-radius:13px;padding:14px}',
        'article h2{margin:0 0 7px;font-size:17px}small{color:#5d6e83}',
        '.thumb{width:100%;height:150px;object-fit:cover;border-radius:9px;background:#e5eaf3}',
        '.item{border-top:1px solid #e7ecf3;padding-top:9px;margin-top:10px}',
        '.tag{display:inline-block;background:#edf1f7;border-radius:7px;padding:3px 7px;margin:5px 0}',
        'a{color:#1353ad}p{overflow-wrap:anywhere}input{padding:10px;border:1px solid #bdcadd;',
        'border-radius:8px;width:min(100%,400px);box-sizing:border-box}',
        '</style></head><body><h1>Kabankalan photo review workspace</h1>',
        '<p class="note">Review dashboard only. Online candidates and local uploads are NOT verified ',
        'by this page. No imports, approvals, or MySQL changes occur here.</p>',
        '<div class="metrics">',
        f'<div class="metric"><b>{len(places)}</b> Kabankalan places</div>',
        f'<div class="metric"><b>{covered}</b> Existing covers</div>',
        f'<div class="metric"><b>{len(places)-covered}</b> Missing covers</div>',
        f'<div class="metric"><b>{pub_missing}</b> Published missing</div>',
        '</div><label for="find">Find a place:</label> ',
        '<input id="find" placeholder="Name or Place ID" oninput="filterCards(this.value)">',
        '<div class="grid" id="cards">'
    ]
    for p in sorted(places.values(), key=lambda p: (not (p.is_active and p.is_verified), p.pk)):
        current_cover = bool(p.cover_image or p.cover_image_url)
        online_candidates = internet_by_id.get(p.pk, [])
        local_review = review_by_id.get(p.pk)
        local_files = files_by_id.get(p.pk, [])
        place_name = escape(p.title)
        parts.append(f'<article data-search="{escape(str(p.pk) + " " + p.title).casefold()}">'
                     f'<h2>{place_name}</h2><small>Place {p.pk} · Kabankalan · '
                     f'{"Published" if p.is_active and p.is_verified else "Not published"}</small>'
                     f'<p><span class="tag">{"Has cover: preserve" if current_cover else "Missing cover"}</span></p>')
        if not current_cover:
            if online_candidates:
                parts.append(f'<p><b>Online Commons candidates: {len(online_candidates)}</b></p>')
                for r in online_candidates[:2]:
                    if online.trusted_https(r.get('image_url'), {'upload.wikimedia.org'}):
                        parts.append(f'<div class="item"><img class="thumb" loading="lazy" '
                                     f'src="{escape(r["image_url"])}" alt="Unverified candidate">')
                        if online.trusted_https(r.get('source_url'), {'commons.wikimedia.org'}):
                            parts.append(f'<p><a href="{escape(r["source_url"])}" '
                                         'target="_blank" rel="noopener noreferrer">Commons file</a></p>')
                        parts.append(f'<small>Review: {escape(r.get("review_decision") or "PENDING")} '
                                     f'· {escape(r.get("license"))} · {escape(r.get("credit"))}</small></div>')
            else:
                parts.append('<p><small>Online candidates: none recorded</small></p>')
            if local_files:
                for f in local_files[:3]:
                    name = f['file_name']
                    if (f['status'] not in ('invalid_image', 'symlink_refused') and local.safe_name(name)
                            and (local.STAGING / name).is_file() and not (local.STAGING / name).is_symlink()):
                        parts.append(f'<div class="item"><img class="thumb" loading="lazy" '
                                     f'src="kabankalan_local_uploads/{quote(name)}" alt="Unverified local file">'
                                     f'<p><small>{escape(name)} · {escape(f["status"])}</small></p></div>')
                    else:
                        parts.append(f'<p><small>Local file: {escape(name)} · {escape(f["status"])}</small></p>')
            if local_review and local_review.get('file_name'):
                parts.append(f'<p><small>Local review: {escape(local_review["file_name"])} · '
                             f'{escape(local_review.get("review_decision") or "PENDING")}</small></p>')
            if not local_files and not (local_review and local_review.get('file_name')):
                parts.append('<p><small>Local files: none staged</small></p>')
        parts.append('</article>')
    parts.extend(['</div>', '<script>function filterCards(v){v=v.toLowerCase();',
                  'document.querySelectorAll("#cards article").forEach(e=>{',
                  'e.hidden=!e.dataset.search.includes(v)});}</script>',
                  '<p class="note">To approve, verify photo identity, source and rights independently in ',
                  'the original CSV reviews. This dashboard has no approval controls.</p>',
                  '</body></html>'])
    local.REVIEW.mkdir(parents=True, exist_ok=True)
    DASHBOARD.write_text(''.join(parts), encoding='utf-8')


class Command(BaseCommand):
    help = 'Combined Kabankalan-only online/local photo review dashboard and checksum staging. No MySQL writes.'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--status', action='store_true', help='Show photo coverage and reviewer counts')
        group.add_argument('--scan-local', action='store_true', help='Read staged local images; write checksum manifest only')
        group.add_argument('--prepare-local', action='store_true', help='Populate only blank filename/checksum CSV cells with backups')
        group.add_argument('--dashboard', action='store_true', help='Build combined read-only HTML dashboard')

    def handle(self, *args, **opts):
        ensure_city()
        places = get_places()
        internet = online_rows()
        reviews = local_rows()
        files = scan(places, reviews)
        if opts['status']:
            covers = sum(bool(p.cover_image or p.cover_image_url) for p in places.values())
            internet_approved = sum(r.get('review_decision', '').strip().lower() == 'approve' for r in internet)
            local_approved = sum(r.get('review_decision', '').strip().lower() == 'approve' for r in reviews)
            self.stdout.write(f'KABANKALAN ONLY: {len(places)} places, {covers} covered, '
                              f'{len(places)-covers} missing covers.')
            self.stdout.write(f'Commons leads: {len(internet)}; approved: {internet_approved}. '
                              f'Local reviewed rows: {len(reviews)}; approved: {local_approved}.')
            self.stdout.write(f'Staged files: {len(files)}; ready to fill CSV: '
                              f'{sum(f["status"] == "ready_for_csv_staging" for f in files)}.')
            self.stdout.write('READ ONLY. Database unchanged.')
            return
        if opts['scan_local']:
            export_manifest(files)
            counts = Counter(r['status'] for r in files)
            self.stdout.write('STAGING SCAN: ' + (', '.join(f'{k}={v}' for k,v in sorted(counts.items())) or 'no files'))
            self.stdout.write(f'MANIFEST: {MANIFEST}\nDatabase and reviewer CSV unchanged.')
            return
        if opts['prepare_local']:
            if not local.CSV_PATH.exists():
                raise CommandError('Run phase6p_local_photo_intake --inventory first.')
            todo = [r for r in files if r['status'] == 'ready_for_csv_staging']
            if not todo:
                self.stdout.write('Nothing ready for CSV preparation. No changes.')
                return
            by_id = {r['place_id']: r for r in reviews}
            for f in todo:
                r = by_id[f['place_id']]
                if r['file_name'] or r['file_sha256'] or (r.get('review_decision') or '').strip():
                    raise CommandError('Reviewer work changed; no changes made.')
            backup = local.CSV_PATH.with_name(local.CSV_PATH.name + '.backup-' +
                                              datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            shutil.copy2(local.CSV_PATH, backup)
            for f in todo:
                r = by_id[f['place_id']]
                r['file_name'], r['file_sha256'] = f['file_name'], f['sha256']
            local.write_rows(reviews)
            local.write_gallery(reviews)
            self.stdout.write(self.style.SUCCESS(f'PREPARED {len(todo)} local CSV row(s); '
                                                'file name and checksum ONLY. No approvals and no MySQL writes.'))
            self.stdout.write('CSV BACKUP: ' + str(backup))
            return
        export_manifest(files)
        render_dashboard(places, internet, reviews, files)
        self.stdout.write(self.style.SUCCESS(f'DASHBOARD READY: {len(places)} Kabankalan records. '
                                            'All photos remain subject to independent review.'))
        self.stdout.write(f'GALLERY: {DASHBOARD}\nMANIFEST: {MANIFEST}\nDatabase unchanged.')
