"""ExploreAnywhere Phase 6P.9 — citywide licensed-photo *lead* search.

No photo is assigned to a Place by this command. Broad names or coordinates
cannot establish which business appears in a photograph. The output is a
standalone review gallery/CSV, never an import queue. MySQL is read-only.

Run under apps/places/management/commands/phase6p_citywide_photos.py.

python manage.py phase6p_citywide_photos --discover --city-id 2
python manage.py phase6p_citywide_photos --status
python manage.py phase6p_citywide_photos --gallery
"""

import csv
import html
import json
import os
import shutil
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from django.core.management.base import BaseCommand, CommandError

from apps.cities.models import City
from apps.places.models import Place
from apps.places.management.commands import phase6p_multisource_photos as multi
from apps.places.management.commands.phase6o_search_commons import commons_search
from apps.places.management.commands.phase6o_business_photos import (
    clean_text, network_json, trusted_https, safe_cell,
)

CITY_ID = 2
CSV_PATH = multi.REPORT_DIR / 'kabankalan_citywide_photo_leads.csv'
HTML_PATH = multi.REPORT_DIR / 'kabankalan_citywide_photo_gallery.html'
STATUS_PATH = multi.REPORT_DIR / 'kabankalan_citywide_photo_status.json'
FIELDS = (
    'provider', 'provider_id', 'search_query', 'title', 'image_url',
    'preview_url', 'source_url', 'credit', 'license', 'license_url',
    'license_supported', 'geo_note', 'suggested_place_id',
    'identity_checked', 'rights_checked', 'review_decision', 'review_notes',
)
REVIEW = ('suggested_place_id', 'identity_checked', 'rights_checked',
          'review_decision', 'review_notes')
CITY_QUERIES = ('Kabankalan', 'Kabankalan Negros Occidental',
                'Mag-aso Falls Kabankalan')
GEO_API = 'https://commons.wikimedia.org/w/api.php'
STATUS_VERSION = 1


def validate_scope():
    city = City.objects.filter(pk=CITY_ID).first()
    if city is None or city.name.strip().casefold() != 'kabankalan':
        raise CommandError('City ID 2 must be Kabankalan. No changes made.')
    return list(Place.objects.filter(city_id=CITY_ID).order_by('pk'))


def load_rows():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames) != set(FIELDS):
            raise CommandError('Citywide CSV schema changed; will not overwrite file.')
        rows = list(reader)
    seen = set()
    for row in rows:
        url = row.get('source_url') or ''
        if not multi.valid_https(url) or url in seen:
            raise CommandError('Citywide CSV invalid/duplicate source; no changes made.')
        if row.get('provider') not in ('openverse', 'commons-text', 'commons-geosearch'):
            raise CommandError('Citywide CSV contains an unexpected provider.')
        seen.add(url)
    return rows


def save_rows(rows):
    multi.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = CSV_PATH.with_suffix('.csv.tmp')
    with temp.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for item in rows:
            writer.writerow({name: safe_cell(item.get(name, '')) for name in FIELDS})
    os.replace(temp, CSV_PATH)


def load_status():
    if not STATUS_PATH.exists():
        return {}
    try:
        obj = json.loads(STATUS_PATH.read_text(encoding='utf-8'))
        if (not isinstance(obj, dict) or obj.get('version') != STATUS_VERSION
                or not isinstance(obj.get('queries'), dict)):
            raise ValueError('Unexpected status format')
        return obj['queries']
    except (OSError, ValueError) as exc:
        raise CommandError('Citywide search cache is invalid; inspect it first.') from exc


def save_status(data):
    multi.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATUS_PATH.with_suffix('.json.tmp')
    temp.write_text(json.dumps({'version': STATUS_VERSION, 'queries': data}, indent=2),
                    encoding='utf-8')
    os.replace(temp, STATUS_PATH)


def photo_center(places):
    # Prefer the Kabankalan Plaza record, only as a search center. Never infer
    # that geotagged photos near it depict the same structure/business.
    for p in places:
        if p.title.strip().casefold() == 'kabankalan plaza' and p.latitude is not None and p.longitude is not None:
            lat, lon = float(p.latitude), float(p.longitude)
            if 4 <= lat <= 22 and 116 <= lon <= 127:
                return lat, lon, 'Kabankalan Plaza coordinates (search anchor only)'
    pairs = []
    for p in places:
        if p.latitude is not None and p.longitude is not None:
            lat, lon = float(p.latitude), float(p.longitude)
            if 4 <= lat <= 22 and 116 <= lon <= 127:
                pairs.append((lat, lon))
    if not pairs:
        return None
    return (statistics.median(x for x, y in pairs),
            statistics.median(y for x, y in pairs),
            'median of geolocated Kabankalan Place records (search anchor only)')


def meta_value(imageinfo, key):
    return str(((imageinfo.get('extmetadata') or {}).get(key) or {}).get('value') or '')


def commons_geosearch(lat, lon, radius_m, limit, agent):
    """Collect geotagged Commons images near a point, never place identities."""
    params = urlencode({
        'action': 'query', 'format': 'json', 'generator': 'geosearch',
        'ggscoord': f'{lat:.6f}|{lon:.6f}', 'ggsradius': radius_m,
        'ggslimit': limit, 'ggsnamespace': 6,
        'prop': 'imageinfo|coordinates',
        'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 620,
    })
    payload = network_json(GEO_API + '?' + params, agent)
    if payload.get('error'):
        raise ValueError('Wikimedia geosearch rejected parameters: ' +
                         clean_text(str(payload['error'].get('code', 'unknown')), 60))
    pages = (payload.get('query') or {}).get('pages') or {}
    if not isinstance(pages, dict):
        raise ValueError('Commons geosearch returned an unexpected page format')
    candidates = []
    for page in pages.values():
        if not isinstance(page, dict) or not str(page.get('title') or '').startswith('File:'):
            continue
        infos = page.get('imageinfo') or []
        if not infos:
            continue
        info = infos[0]
        if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
            continue
        image_url = info.get('thumburl') or info.get('url') or ''
        source_url = info.get('descriptionurl') or ''
        if (not trusted_https(image_url, {'upload.wikimedia.org'}) or
                not trusted_https(source_url, {'commons.wikimedia.org'})):
            continue
        license_name = clean_text(meta_value(info, 'LicenseShortName'), 100)
        license_url = clean_text(meta_value(info, 'LicenseUrl'), 500)
        credit = clean_text(meta_value(info, 'Artist') or meta_value(info, 'Attribution'), 500)
        geo_note = 'Geosearch result: file position may not identify pictured subject'
        candidates.append({
            'provider': 'commons-geosearch', 'provider_id': str(page.get('pageid') or ''),
            'search_query': f'Commons geosearch radius {radius_m}m from ({lat:.6f}, {lon:.6f})',
            'title': clean_text(page.get('title'), 300), 'image_url': image_url,
            'preview_url': image_url, 'source_url': source_url,
            'credit': credit, 'license': license_name, 'license_url': license_url,
            'license_supported': 'yes' if license_name in multi.SUPPORTED else 'no',
            'geo_note': geo_note,
        })
    return candidates


def commons_text_candidates(query, limit, agent):
    return [{
        'provider': 'commons-text', 'provider_id': c.get('file_title', ''),
        'search_query': query, 'title': c.get('file_title', ''),
        'image_url': c.get('image_url', ''),
        'preview_url': c.get('image_url', ''),
        'source_url': c.get('source_url', ''),
        'credit': c.get('credit', ''), 'license': c.get('license', ''),
        'license_url': c.get('license_url', ''),
        'license_supported': 'yes' if c.get('license') in multi.SUPPORTED else 'no',
        'geo_note': '',
    } for c in commons_search(query, agent, limit)]


def html_gallery(rows):
    def esc(s):
        return html.escape(str(s or ''), quote=True)
    out = ['<!doctype html><html lang="en"><head><meta charset="utf-8">',
           '<meta name="viewport" content="width=device-width, initial-scale=1">',
           '<title>ExploreAnywhere | Kabankalan Citywide Photo Leads</title>',
           '<style>body{font:15px system-ui,sans-serif;max-width:1250px;margin:30px auto;',
           'padding:0 16px;background:#f6f8fc;color:#172d4b}.grid{display:grid;',
           'grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px}',
           'article{background:#fff;border:1px solid #d8e1ed;border-radius:11px;',
           'overflow:hidden}img{width:100%;height:175px;object-fit:cover;',
           'background:#e9eff8}.body{padding:12px}small{color:#53677e}',
           'a{color:#1556a4}p{overflow-wrap:anywhere}.note{background:#fff;',
           'padding:12px;border:1px solid #d8e1ed;border-radius:9px}</style>',
           '</head><body><h1>Kabankalan citywide photo discovery</h1>',
           f'<p>{len(rows)} leads (not verified or assigned to any Place).</p>',
           '<p class="note"><strong>Photos here are NOT assigned to any business.</strong> ',
           'A citywide search or location tag does not prove a photo depicts a particular ',
           'Place. Check the original image page, exact location/identity, creator, ',
           'license and any required attribution before separately using the ',
           'established photo-review workflow. No automatic downloads or imports.</p>',
           '<main class="grid">']
    for row in rows:
        url = row.get('source_url', '')
        if not multi.valid_https(url):
            continue
        preview = row.get('preview_url', '')
        out.append('<article>')
        if multi.valid_https(preview):
            out.append(f'<img loading="lazy" referrerpolicy="no-referrer" src="{esc(preview)}" alt="Unverified Kabankalan photo candidate">')
        out.append('<div class="body">'
                   f'<small>{esc(row.get("provider"))} | {esc(row.get("search_query"))}</small>'
                   f'<h3>{esc(row.get("title"))}</h3>'
                   f'<p>Credit: {esc(row.get("credit") or "Unknown")}</p>'
                   f'<p>License: {esc(row.get("license") or "Unknown")} '
                   f'({"supported" if row.get("license_supported") == "yes" else "needs rights verification"})</p>'
                   f'<p><a href="{esc(url)}" target="_blank" rel="noopener noreferrer">Review original source</a></p>'
                   '<small>IDENTITY UNVERIFIED · NOT APPROVED FOR IMPORT</small>'
                   '</div></article>')
    if not rows:
        out.append('<p>No candidates collected yet.</p>')
    out.append('</main></body></html>')
    multi.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = HTML_PATH.with_suffix('.html.tmp')
    tmp.write_text(''.join(out), encoding='utf-8')
    os.replace(tmp, HTML_PATH)


class Command(BaseCommand):
    help = 'Citywide Kabankalan photos: Openverse, Commons text and geotagged leads; NO assignments/imports.'

    def add_arguments(self, parser):
        mode = parser.add_mutually_exclusive_group(required=True)
        mode.add_argument('--discover', action='store_true')
        mode.add_argument('--status', action='store_true')
        mode.add_argument('--gallery', action='store_true')
        parser.add_argument('--city-id', type=int, default=CITY_ID)
        parser.add_argument('--per-query', type=int, default=8,
                            help='Maximum leads per query, 1-20; default 8')
        parser.add_argument('--radius', type=int, default=5000,
                            help='Commons geotag search radius in meters, 100-10000')
        parser.add_argument('--rescan', action='store_true',
                            help='Repeat successful prior queries; preserve reviewer notes')
        parser.add_argument('--sources', default='openverse,commons,geo',
                            help='Comma-separated: openverse,commons,geo')

    def handle(self, *args, **opts):
        if opts['city_id'] != CITY_ID:
            raise CommandError('Only --city-id 2 (Kabankalan) allowed.')
        if opts['rescan'] and not opts['discover']:
            raise CommandError('--rescan requires --discover.')
        if not 1 <= opts['per_query'] <= 20 or not 100 <= opts['radius'] <= 10000:
            raise CommandError('Use --per-query 1-20 and --radius 100-10000.')
        source_list = [s.strip().lower() for s in opts['sources'].split(',') if s.strip()]
        if (not source_list or len(set(source_list)) != len(source_list)
                or set(source_list) - {'openverse', 'commons', 'geo'}):
            raise CommandError('Use --sources openverse,commons,geo or a subset.')
        places = validate_scope()
        rows = load_rows()
        if opts['status']:
            counts = {p: sum(r['provider'] == p for r in rows)
                      for p in ('openverse', 'commons-text', 'commons-geosearch')}
            self.stdout.write(f'CITY 2 KABANKALAN: {len(places)} places; '
                              f'{sum(not (p.cover_image or p.cover_image_url) for p in places)} missing covers.')
            self.stdout.write(f'Unassigned citywide leads: {len(rows)}; breakdown: {counts}')
            self.stdout.write('READ ONLY; no photos assigned, approved or imported.')
            return
        if opts['gallery']:
            html_gallery(rows)
            self.stdout.write(f'REVIEW GALLERY: {HTML_PATH} | {len(rows)} unassigned leads.')
            return
        self.discover(places, rows, source_list, opts)

    def discover(self, places, rows, sources, opts):
        agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
        if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT to a real contact email.')
        try:
            import truststore
        except ImportError as exc:
            raise CommandError('Install truststore: python -m pip install truststore') from exc
        truststore.inject_into_ssl()
        self.stdout.write('HTTPS: verified using Windows/system truststore.')
        self.stdout.write('CITY 2 ONLY: discovery is READ ONLY for MySQL; no automatic identity matching.')
        status = load_status()
        already = {r['source_url'] for r in rows}
        backup_created = False
        added = 0
        errors = 0
        cached = 0

        def query_one(key, fetcher):
            nonlocal backup_created, added, errors, cached
            if not opts['rescan'] and status.get(key) == 'success':
                cached += 1
                self.stdout.write('SKIP cached ' + key)
                return
            try:
                found = fetcher()
                self.stdout.write(f'{key}: {len(found)} photo leads')
                new = []
                for candidate in found:
                    source = candidate.get('source_url') or ''
                    if not multi.valid_https(source) or source in already:
                        continue
                    already.add(source)
                    new.append({**candidate, **{field: '' for field in REVIEW}})
                if new:
                    if CSV_PATH.exists() and not backup_created:
                        backup = CSV_PATH.with_name(CSV_PATH.name + '.backup-' +
                                                    datetime.now().strftime('%Y%m%d-%H%M%S'))
                        shutil.copy2(CSV_PATH, backup)
                        backup_created = True
                        self.stdout.write('CSV backup: ' + str(backup))
                    rows.extend(new)
                    save_rows(rows)
                    added += len(new)
                status[key] = 'success'  # Only successful calls are cached (including zero-result).
                save_status(status)
            except (HTTPError, URLError, TimeoutError, OSError, ValueError,
                    KeyError, UnicodeError, json.JSONDecodeError) as exc:
                errors += 1
                self.stdout.write('API WARNING ' + key + ': ' + multi.safe_error(exc))
            time.sleep(1)

        for query in CITY_QUERIES:
            if 'openverse' in sources:
                query_one('openverse:' + query,
                          lambda q=query: multi.openverse_candidates(q, opts['per_query'], agent))
            if 'commons' in sources:
                query_one('commons:' + query,
                          lambda q=query: commons_text_candidates(q, opts['per_query'], agent))
        if 'geo' in sources:
            center = photo_center(places)
            if center is not None:
                lat, lon, label = center
                self.stdout.write('Geo search anchor: ' + label)
                key = f'geo:{lat:.6f}:{lon:.6f}:{opts["radius"]}'
                query_one(key, lambda: commons_geosearch(
                    lat, lon, opts['radius'], opts['per_query'], agent))
            else:
                self.stdout.write('GEO SKIPPED: no reliable stored Kabankalan coordinates.')
        if not CSV_PATH.exists():
            save_rows(rows)
        html_gallery(rows)
        self.stdout.write(self.style.SUCCESS(
            f'CITYWIDE DISCOVERY COMPLETE: {added} new unassigned leads, '
            f'{cached} cached queries, {errors} API warnings.'))
        self.stdout.write('CSV: ' + str(CSV_PATH))
        self.stdout.write('GALLERY: ' + str(HTML_PATH))
        self.stdout.write('Database unchanged. NO place assignments, approvals, downloads, or imports.')
