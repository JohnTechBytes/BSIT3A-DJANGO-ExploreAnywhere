"""ExploreAnywhere Phase 6P.11 — Kabankalan verified-photo collection queue.

Install: apps/places/management/commands/phase6p11_verified_photo_queue.py

Only queries city_id=2 (confirmed as Kabankalan). No database writes, network
requests, image downloads, approvals, or imports. Never alters collector CSVs.

python manage.py phase6p11_verified_photo_queue --build --city-id 2
python manage.py phase6p11_verified_photo_queue --preview --city-id 2
python manage.py phase6p11_verified_photo_queue --gallery --city-id 2
"""

import csv
import hashlib
import html
import ipaddress
import os
import re
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.cities.models import City
from apps.places.models import Place

CITY_ID = 2
BASE = Path(settings.BASE_DIR) / 'phase6_photo_review'
QUEUE = BASE / 'kabankalan_phase6p11_priority_queue.csv'
REVIEWS = BASE / 'kabankalan_phase6p11_candidate_reviews.csv'
GALLERY = BASE / 'kabankalan_phase6p11_review.html'

SOURCES = (
    ('citywide', BASE / 'kabankalan_citywide_photo_leads.csv'),
    ('multisource', BASE / 'kabankalan_multisource_photo_candidates.csv'),
    ('commons', BASE / 'all_cities_photo_candidates.csv'),
)
FOCUS = {'kabankalan plaza', 'maronggues hill', 'mount nai-guin', 'mount luyang', 'amyan hill'}
SUPPORTED_LICENSES = {
    'CC BY 4.0', 'CC BY 3.0', 'CC BY-SA 4.0', 'CC BY-SA 3.0', 'CC0 1.0',
}
QUEUE_FIELDS = (
    'place_id', 'place_title', 'priority', 'publication', 'cover_status',
    'location_hint', 'openverse_search', 'commons_search', 'collection_notes',
)
REVIEW_FIELDS = (
    'candidate_id', 'origin', 'collector_place_id', 'provider', 'photo_title',
    'source_url', 'image_url', 'credit', 'license', 'license_url',
    'linked_place_id', 'confirmed_place_title', 'review_decision',
    'identity_checked', 'rights_checked', 'identity_evidence', 'rights_evidence',
    'reviewer', 'review_notes',
)
MANUAL_FIELDS = (
    'linked_place_id', 'confirmed_place_title', 'review_decision',
    'identity_checked', 'rights_checked', 'identity_evidence', 'rights_evidence',
    'reviewer', 'review_notes',
)


def safe_https(url):
    if not isinstance(url, str) or len(url) > 2000 or any(c.isspace() for c in url):
        return False
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username
                or parsed.password or parsed.port not in (None, 443)
                or parsed.fragment):
            return False
        host = parsed.hostname.lower()
        if host == 'localhost' or host.endswith(('.local', '.internal')):
            return False
        try:
            return ipaddress.ip_address(host).is_global
        except ValueError:
            return True
    except (TypeError, ValueError):
        return False


def safe_cell(value):
    """Prevent formula execution when CSV opened in Excel."""
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', ' ', str(value or '')).strip()
    return "'" + text if text.lstrip().startswith(('=', '+', '-', '@')) else text


def esc(value):
    return html.escape(str(value or ''), quote=True)


def load_csv(path, required, expected=None):
    if not path.exists():
        return []
    if path.is_symlink() or path.stat().st_size > 3_000_000:
        raise CommandError(f'Unsafe or oversized input file: {path.name}')
    with path.open('r', encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not set(required).issubset(reader.fieldnames):
            raise CommandError(f'{path.name}: expected CSV columns not found; nothing overwritten.')
        rows = list(reader)
    if len(rows) > 10000:
        raise CommandError(f'{path.name}: too many rows.')
    if expected is not None and len(rows) != expected:
        raise CommandError(f'{path.name}: expected {expected} rows.')
    return rows


def snapshot_write(path, headers, rows):
    """Write own artifacts only; timestamped backup; atomic replace."""
    BASE.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise CommandError(f'Refusing symlink output: {path.name}')
    tmp = path.with_name(path.name + '.tmp')
    if tmp.exists():
        raise CommandError(f'Previous temporary output exists: {tmp.name}; inspect first.')
    if path.exists():
        backup = path.with_name(path.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        shutil.copy2(path, backup)
    try:
        with tmp.open('x', encoding='utf-8-sig', newline='') as stream:
            writer = csv.DictWriter(stream, fieldnames=headers)
            writer.writeheader()
            for row in rows:
                writer.writerow({k: safe_cell(row.get(k, '')) for k in headers})
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def check_city():
    city = City.objects.filter(pk=CITY_ID).first()
    if not city or city.name.strip().casefold() != 'kabankalan':
        raise CommandError('City ID 2 is not confirmed as Kabankalan. Stopped.')
    places = list(Place.objects.filter(city_id=CITY_ID).order_by('pk'))
    return {p.pk: p for p in places}


def priority(place):
    if place.cover_image or place.cover_image_url:
        return 'COVERED - PRESERVE'
    if place.title.strip().casefold() in FOCUS:
        return 'P1 - existing attraction'
    if place.is_active and place.is_verified:
        return 'P1 - published/verified'
    return 'P2 - remaining business/place'


def make_priority_rows(places, previous_rows):
    notes = {r['place_id']: r.get('collection_notes', '') for r in previous_rows}
    rows = []
    for p in places.values():
        query = p.title.strip() + ' Kabankalan Negros Occidental'
        rows.append({
            'place_id': str(p.pk), 'place_title': p.title, 'priority': priority(p),
            'publication': 'published/verified' if p.is_active and p.is_verified else 'not published/verified',
            'cover_status': 'HAS COVER - NEVER OVERWRITE' if p.cover_image or p.cover_image_url else 'MISSING',
            'location_hint': f'{p.barangay}, {p.address}'.strip(' ,')[:280],
            'openverse_search': 'https://openverse.org/search/image?q=' + quote(query),
            'commons_search': 'https://commons.wikimedia.org/wiki/Special:MediaSearch?type=image&search=' + quote(query),
            'collection_notes': notes.get(str(p.pk), ''),
        })
    rank = {'P1 - existing attraction': 0, 'P1 - published/verified': 1,
            'P2 - remaining business/place': 2, 'COVERED - PRESERVE': 3}
    return sorted(rows, key=lambda r: (rank[r['priority']], int(r['place_id'])))


def source_candidates(places):
    results = {}
    for origin, path in SOURCES:
        required = ('source_url', 'image_url', 'credit', 'license', 'license_url')
        rows = load_csv(path, required)
        for r in rows:
            # Citywide leads are unassigned. Collectors' place IDs are only search hints.
            collector_id = ''
            if origin in ('multisource', 'commons'):
                if r.get('city_id') != str(CITY_ID):
                    continue
                collector_id = (r.get('place_id') or '').strip()
                if not collector_id.isascii() or not collector_id.isdecimal() or int(collector_id) not in places:
                    raise CommandError(f'{path.name}: malformed place ID within Kabankalan rows.')
            source_url = (r.get('source_url') or '').strip()
            if not safe_https(source_url):
                # Invalid URLs are never written to the reviewer file.
                continue
            provider = (r.get('provider') or 'commons').strip().lower()
            if origin == 'commons':
                provider = 'commons'
            photo_title = (r.get('title') or r.get('file_title') or '').strip()
            keydata = '\x1f'.join((origin, collector_id, provider, source_url))
            key = hashlib.sha256(keydata.encode('utf-8')).hexdigest()[:20]
            if key in results:
                continue
            results[key] = {
                'candidate_id': key, 'origin': origin, 'collector_place_id': collector_id,
                'provider': provider, 'photo_title': photo_title,
                'source_url': source_url,
                'image_url': r.get('image_url') or '',
                'credit': r.get('credit') or '', 'license': r.get('license') or '',
                'license_url': r.get('license_url') or '',
                **{k: '' for k in MANUAL_FIELDS},
            }
    return results


def combine_reviews(places, old):
    generated = source_candidates(places)
    previous = {}
    for row in old:
        key = row.get('candidate_id')
        if key in previous:
            raise CommandError('Duplicate reviewer candidate_id; no files changed.')
        previous[key] = row
    out = []
    for key, row in generated.items():
        if key in previous:
            # Preserve the entire prior row including attribution & manually edited fields.
            out.append(previous.pop(key))
        else:
            out.append(row)
    # Never drop prior reviewer decisions even when source CSV changes.
    out.extend(previous.values())
    return out


def candidate_issues(row, places, used_sources=None):
    """Documentation check only. Passing != permission or import authorization."""
    problems = []
    ident = str(row.get('linked_place_id') or '').strip()
    place = places.get(int(ident)) if ident.isascii() and ident.isdecimal() else None
    if place is None:
        problems.append('Missing or non-Kabankalan linked Place ID')
    else:
        if place.cover_image or place.cover_image_url:
            problems.append('Place already has a cover; preserve it')
        if row.get('confirmed_place_title', '').strip() != place.title:
            problems.append('Confirmed title must match the current Django Place.title')
        expected = (row.get('collector_place_id') or '').strip()
        if expected and expected != ident:
            problems.append('Collector place differs from review destination; investigate manually')
    if row.get('identity_checked', '').strip().lower() != 'yes':
        problems.append('Identity has not been checked')
    if row.get('rights_checked', '').strip().lower() != 'yes':
        problems.append('Rights have not been checked')
    if len((row.get('identity_evidence') or '').strip()) < 30:
        problems.append('Provide substantive place-identity evidence (30+ characters)')
    if len((row.get('rights_evidence') or '').strip()) < 30:
        problems.append('Provide source-page licensing/permission evidence (30+ characters)')
    if len((row.get('review_notes') or '').strip()) < 20:
        problems.append('Provide reviewer notes (20+ characters)')
    if not row.get('reviewer', '').strip():
        problems.append('Named reviewer required')
    if (row.get('license') or '').strip() not in SUPPORTED_LICENSES:
        problems.append('Unsupported or unverified license label')
    if not row.get('credit', '').strip():
        problems.append('Photographer attribution is missing')
    if not safe_https(row.get('source_url') or '') or not safe_https(row.get('license_url') or ''):
        problems.append('Original HTTPS source page and license URL required')
    if not safe_https(row.get('image_url') or ''):
        problems.append('Image URL must be public HTTPS')
    if re.search(r'\b(locator|montage|map|barangays of kabankalan)\b',
                 (row.get('photo_title') or '').casefold()):
        problems.append('Map/montage unsuitable as individual Place cover')
    if used_sources is not None:
        url = (row.get('source_url') or '').strip()
        if url and len(used_sources.get(url, set())) > 1:
            problems.append('Same source photo linked to multiple different places')
    return problems


def evaluate(rows, places):
    approved = [r for r in rows if (r.get('review_decision') or '').strip().lower() == 'approve']
    sources = {}
    for r in approved:
        url = (r.get('source_url') or '').strip()
        pid = (r.get('linked_place_id') or '').strip()
        sources.setdefault(url, set()).add(pid)
    return [(r, candidate_issues(r, places, sources)) for r in approved]


def make_html(places, queue, reviews):
    outcome = {r['candidate_id']: issues for r, issues in evaluate(reviews, places)}
    missing = sum(not (p.cover_image or p.cover_image_url) for p in places.values())
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>ExploreAnywhere | Kabankalan Verified Photo Queue</title>',
        '<style>body{font:14px system-ui,sans-serif;max-width:1350px;margin:25px auto;padding:0 18px;',
        'color:#233348;background:#f6f8fc}h1{font-size:26px}h2{font-size:19px}',
        '.stats,.grid{display:grid;gap:12px;grid-template-columns:repeat(auto-fit,minmax(250px,1fr))}',
        '.tile,article{padding:14px;background:white;border:1px solid #d9e2ef;border-radius:12px}',
        'a{color:#13579f}small{color:#53657c}.warn{background:#fff9ec;padding:14px;',
        'border:1px solid #dfca9a;border-radius:9px}img{height:140px;width:100%;object-fit:cover;',
        'background:#e8eff7;border-radius:8px}p{overflow-wrap:anywhere}',
        'input{padding:10px;width:min(100%,420px);border-radius:8px;border:1px solid #c2cbd7}',
        '</style></head><body>',
        '<h1>Kabankalan • Phase 6P.11 verified-photo collection queue</h1>',
        '<p class="warn"><b>Review-only:</b> Source search, metadata, image proximity, and CSV flags ',
        'do not verify identity, rights or photograph authenticity. This tool never imports or ',
        'approves any image, creates Place records, or alters MySQL.</p>',
        '<div class="stats">',
        f'<div class="tile"><strong>{len(places)}</strong> Kabankalan places</div>',
        f'<div class="tile"><strong>{missing}</strong> missing covers</div>',
        f'<div class="tile"><strong>{len(reviews)}</strong> candidate source rows</div>',
        f'<div class="tile"><strong>{sum(not issues for _, issues in evaluate(reviews, places))}</strong> reviewed rows passing documentation checks (not imported)</div>',
        '</div><h2>Priority collection targets</h2>',
        '<p><small>Covered places remain in the CSV for audit only. ',
        'Search results must depict the exact destination, not just Kabankalan.</small></p>',
        '<input id="search" placeholder="Filter places or candidate titles" oninput="filterAll(this.value)">',
        '<div class="grid">',
    ]
    for item in queue:
        if item['priority'].startswith('COVERED'):
            continue
        parts.append('<article class="searchable" data-search="' + esc((item['place_id'] + ' ' + item['place_title']).casefold()) + '">')
        parts.append('<strong>' + esc(item['place_title']) + '</strong> <small>#' + esc(item['place_id']) + '</small>')
        parts.append('<p><small>' + esc(item['priority']) + '</small></p>')
        parts.append('<p><a href="' + esc(item['commons_search']) + '" target="_blank" rel="noopener noreferrer">Commons search</a> · ')
        parts.append('<a href="' + esc(item['openverse_search']) + '" target="_blank" rel="noopener noreferrer">Openverse search</a></p>')
        parts.append('</article>')
    parts.append('</div><h2>Discovered images — unverified review candidates</h2><div class="grid">')
    for r in reviews:
        if not safe_https(r.get('source_url') or ''):
            continue
        status = (r.get('review_decision') or '').strip().lower()
        issues = outcome.get(r['candidate_id'])
        parts.append('<article class="searchable" data-search="' + esc((r.get('photo_title','') + ' ' + r.get('linked_place_id','')).casefold()) + '">')
        if safe_https(r.get('image_url') or ''):
            parts.append('<img loading="lazy" src="' + esc(r['image_url']) + '" alt="Unverified candidate photo">')
        parts.append('<p><strong>' + esc(r.get('photo_title')) + '</strong></p>')
        parts.append('<p><small>' + esc(r.get('provider')) + ' · ' + esc(r.get('license')) + ' · ' + esc(r.get('credit')) + '</small></p>')
        parts.append('<p><a href="' + esc(r['source_url']) + '" target="_blank" rel="noopener noreferrer">Original source page</a></p>')
        parts.append('<p><small>Assigned by reviewer: ' + esc(r.get('linked_place_id') or 'none') + ' · Decision: ' + esc(status or 'pending') + '</small></p>')
        if status == 'approve':
            parts.append('<p><small>Documentation: ' + ('needs correction — ' + esc('; '.join(issues)) if issues else 'complete; requires separate genuine approval/import') + '</small></p>')
        parts.append('</article>')
    parts.append('</div><script>function filterAll(v){v=v.toLowerCase();document.querySelectorAll(".searchable").forEach(e=>{e.hidden=!e.dataset.search.includes(v)})}</script></body></html>')
    BASE.mkdir(parents=True, exist_ok=True)
    if GALLERY.is_symlink():
        raise CommandError('Refusing symlink review gallery.')
    GALLERY.write_text(''.join(parts), encoding='utf-8')


class Command(BaseCommand):
    help = 'Kabankalan-only verified-photo search queue & candidate review; no DB writes or imports.'

    def add_arguments(self, parser):
        modes = parser.add_mutually_exclusive_group(required=True)
        modes.add_argument('--build', action='store_true', help='Build or refresh the CSV queues while preserving manual reviews')
        modes.add_argument('--preview', action='store_true', help='Check manually marked approvals without importing')
        modes.add_argument('--gallery', action='store_true', help='Regenerate static review gallery; no DB writes')
        modes.add_argument('--status', action='store_true', help='Show Kabankalan photo queue counts')
        parser.add_argument('--city-id', type=int, default=CITY_ID)

    def handle(self, *args, **options):
        if options['city_id'] != CITY_ID:
            raise CommandError('Only --city-id 2 (Kabankalan) is allowed.')
        places = check_city()
        if options['build']:
            old_q = load_csv(QUEUE, QUEUE_FIELDS)
            old_review = load_csv(REVIEWS, REVIEW_FIELDS)
            queue = make_priority_rows(places, old_q)
            review = combine_reviews(places, old_review)
            # Perform all validation before touching either output.
            if len({r['place_id'] for r in queue}) != len(places):
                raise CommandError('Duplicate/missing priority records detected.')
            if len({r['candidate_id'] for r in review}) != len(review):
                raise CommandError('Duplicate review candidate IDs detected.')
            snapshot_write(QUEUE, QUEUE_FIELDS, queue)
            snapshot_write(REVIEWS, REVIEW_FIELDS, review)
            make_html(places, queue, review)
            self.stdout.write(f'BUILD COMPLETE: {len(places)} Kabankalan places, '
                              f'{sum(not (p.cover_image or p.cover_image_url) for p in places.values())} missing covers, '
                              f'{len(review)} candidate rows; approvals preserved.')
            self.stdout.write(f'PRIORITY CSV: {QUEUE}\nREVIEW CSV: {REVIEWS}\nGALLERY: {GALLERY}')
            self.stdout.write('NO DATABASE WRITES. NO AUTOMATIC ASSIGNMENTS, APPROVALS OR IMPORTS.')
            return
        queue = load_csv(QUEUE, QUEUE_FIELDS)
        review = load_csv(REVIEWS, REVIEW_FIELDS)
        if not queue:
            raise CommandError('First run --build to create the Phase 6P.11 queue.')
        if options['status']:
            priorities = Counter(r['priority'] for r in queue)
            outcome = evaluate(review, places)
            self.stdout.write(f'KABANKALAN: {len(places)} places; '
                              f'{sum(not (p.cover_image or p.cover_image_url) for p in places.values())} missing covers.')
            self.stdout.write(f'PRIORITY: {dict(priorities)}')
            self.stdout.write(f'CANDIDATES: {len(review)}; manual approve flags: {len(outcome)}; '
                              f'documentation complete: {sum(not errors for _, errors in outcome)}.')
        elif options['preview']:
            outcome = evaluate(review, places)
            if not outcome:
                self.stdout.write('PREVIEW: no manually approved candidates; no images ready for import.')
            for row, problems in outcome:
                label = 'BLOCKED' if problems else 'DOCUMENTATION COMPLETE (NOT IMPORTED)'
                self.stdout.write(f'{label} | {row["candidate_id"]} | '
                                  f'Place {row.get("linked_place_id") or "unassigned"}')
                for reason in problems:
                    self.stdout.write('  - ' + reason)
            self.stdout.write(f'REVIEW CHECKS: {len(outcome)} marked approve, '
                              f'{sum(not err for _, err in outcome)} documentation-complete; '
                              'ALL images still require independent human verification and separate safe import.')
        elif options['gallery']:
            make_html(places, queue, review)
            self.stdout.write(f'REVIEW GALLERY: {GALLERY} | {len(review)} leads.')
        self.stdout.write('READ ONLY for MySQL. Existing covers and all other cities untouched.')
