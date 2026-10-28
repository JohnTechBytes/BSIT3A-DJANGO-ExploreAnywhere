"""ExploreAnywhere Phase 6P.8 — Kabankalan-only multi-source PHOTO DISCOVERY.

Install in apps/places/management/commands/phase6p_multisource_photos.py.

Sources:
  * Openverse search API (public endpoint; no token for small read-only searches)
  * Flickr API, optional: EXPLOREANYWHERE_FLICKR_API_KEY
  * Existing reviewed Wikimedia Commons collector, unchanged and cache-aware

All sources provide UNVERIFIED search leads, not proof of place identity or rights.
The multi-source CSV is separate from the Commons-only import CSV because that
importer rejects non-Wikimedia URLs. No mode imports, downloads, approves, or
changes Place or PlacePhoto. Covers are never overwritten. city_id=2 enforced.

Modes:
  --discover [--offset 0 --limit 5 --per-query 2 --sources all]
  --status
  --gallery
"""

import csv
import html
import ipaddress
import json
import os
import re
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import Request, urlopen

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.cities.models import City
from apps.places.models import Place
from apps.places.management.commands import phase6p_bulk_photos as commons_bulk

CITY_ID = 2
REPORT_DIR = commons_bulk.REPORT_DIR
CSV_PATH = REPORT_DIR / 'kabankalan_multisource_photo_candidates.csv'
HTML_PATH = REPORT_DIR / 'kabankalan_multisource_photo_gallery.html'
STATUS_PATH = REPORT_DIR / 'kabankalan_multisource_discovery_status.json'
SCHEMA = 1
SEARCH_VERSION = 1
OPENVERSE_API = 'https://api.openverse.org/v1/images/'
FLICKR_API = 'https://www.flickr.com/services/rest/'
SOURCES = ('openverse', 'flickr', 'commons')
MAX_JSON_BYTES = 4 * 1024 * 1024
FIELDS = (
    'place_id', 'city_id', 'place_slug', 'place_name', 'latitude', 'longitude',
    'provider', 'provider_id', 'search_query', 'title', 'preview_url',
    'image_url', 'source_url', 'credit', 'license', 'license_url',
    'license_supported', 'identity_status', 'review_decision',
    'identity_checked', 'rights_checked', 'review_notes',
)
REVIEW_FIELDS = ('review_decision', 'identity_checked', 'rights_checked', 'review_notes')
SUPPORTED = {
    'CC BY 4.0', 'CC BY 3.0', 'CC BY-SA 4.0', 'CC BY-SA 3.0', 'CC0 1.0'
}
FLICKR_LICENSES = {
    '4': ('CC BY 2.0', 'https://creativecommons.org/licenses/by/2.0/'),
    '5': ('CC BY-SA 2.0', 'https://creativecommons.org/licenses/by-sa/2.0/'),
    '9': ('CC0 1.0', 'https://creativecommons.org/publicdomain/zero/1.0/'),
}


def valid_https(url, hosts=None):
    """URLs are display links only, never fetched by this collector."""
    if not isinstance(url, str) or len(url) > 2000 or any(c.isspace() for c in url):
        return False
    try:
        p = urlsplit(url)
        if (p.scheme != 'https' or not p.hostname or p.username or p.password
                or p.port not in (None, 443) or p.fragment):
            return False
        host = p.hostname.lower()
        if host == 'localhost' or host.endswith(('.local', '.internal')):
            return False
        try:
            if not ipaddress.ip_address(host).is_global:
                return False
        except ValueError:
            pass  # Public DNS hostname; the collector does not fetch this link.
        if hosts is not None and host not in hosts:
            return False
        return True
    except (TypeError, ValueError):
        return False


def clean_text(value, limit=300):
    return re.sub(r'[\x00-\x1f\x7f]+', ' ', str(value or '')).strip()[:limit]


def license_from_openverse(item):
    """Only license families permitting reuse; CC 2.0 flagged for adaptation."""
    code = str(item.get('license') or '').strip().lower()
    version = str(item.get('license_version') or '').strip()
    if code == 'cc0':
        return 'CC0 1.0', 'https://creativecommons.org/publicdomain/zero/1.0/'
    if code in ('by', 'by-sa') and version in ('2.0', '3.0', '4.0'):
        base = f'https://creativecommons.org/licenses/{code}/{version}/'
        return f'CC {code.upper()} {version}', base
    return None


def photo_queries(name):
    text = re.sub(r'\s+', ' ', str(name or '')).replace('"', '').strip()[:85]
    if not text:
        return ()
    # Qualification is a search hint, NOT proof that the photo belongs to place.
    result = [f'{text} Kabankalan', f'{text} Negros Occidental']
    return tuple(dict.fromkeys(result))


def api_json(url, params, agent):
    """Fetch only hard-coded trusted public API endpoints with TLS verification."""
    if url not in (OPENVERSE_API, FLICKR_API):
        raise ValueError('Unrecognized photo API endpoint')
    uri = url + '?' + urlencode(params)
    req = Request(uri, headers={
        'User-Agent': agent, 'Accept': 'application/json',
    })
    with urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise ValueError('Photo API returned a non-200 status')
        data = response.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise ValueError('Photo API response larger than 4 MB')
    parsed = json.loads(data.decode('utf-8'))
    if not isinstance(parsed, dict):
        raise ValueError('Photo API JSON was not an object')
    return parsed


def openverse_candidates(query, per_query, agent):
    payload = api_json(OPENVERSE_API, {
        'q': query,
        'page_size': per_query,
        'license': 'by,by-sa,cc0',
    }, agent)
    result = payload.get('results')
    if not isinstance(result, list):
        raise ValueError('Openverse returned unexpected results format')
    candidates = []
    for item in result[:per_query]:
        if not isinstance(item, dict):
            continue
        lic = license_from_openverse(item)
        if lic is None:
            continue  # No NC, ND, unknown or incompatible copyright assumptions
        license_name, license_url = lic
        source_url = item.get('foreign_landing_url') or ''
        image_url = item.get('url') or ''
        thumbnail = item.get('thumbnail') or ''
        if not valid_https(source_url):
            continue
        if not valid_https(image_url):
            image_url = ''
        if not valid_https(thumbnail):
            thumbnail = ''
        if not image_url and not thumbnail:
            continue
        candidates.append({
            'provider': 'openverse', 'provider_id': clean_text(item.get('id'), 120),
            'title': clean_text(item.get('title'), 250),
            'preview_url': thumbnail or image_url,
            'image_url': image_url,
            'source_url': source_url,
            'credit': clean_text(item.get('creator'), 300),
            'license': license_name, 'license_url': license_url,
            'license_supported': 'yes' if license_name in SUPPORTED else 'no',
            'identity_status': 'UNVERIFIED — exact place must be independently confirmed',
        })
    return candidates


def flickr_candidates(query, per_query, agent, api_key):
    if not api_key:
        raise ValueError('Flickr key not configured')
    payload = api_json(FLICKR_API, {
        'method': 'flickr.photos.search', 'api_key': api_key,
        'text': query, 'license': '4,5,9',
        'media': 'photos', 'safe_search': '1', 'content_type': '1',
        'per_page': str(per_query), 'page': '1',
        'extras': 'owner_name,url_q,url_m', 'format': 'json',
        'nojsoncallback': '1', 'sort': 'relevance',
    }, agent)
    if payload.get('stat') != 'ok':
        # Do not echo payload: it may include environment-specific account details.
        raise ValueError('Flickr API reported failure (verify API key and quota)')
    photos = payload.get('photos')
    if not isinstance(photos, dict) or not isinstance(photos.get('photo'), list):
        raise ValueError('Flickr returned unexpected results format')
    candidates = []
    for item in photos['photo'][:per_query]:
        if not isinstance(item, dict):
            continue
        lic = FLICKR_LICENSES.get(str(item.get('license') or ''))
        if not lic:
            continue
        pid = str(item.get('id') or '')
        owner = str(item.get('owner') or '')
        if not pid.isascii() or not pid.isdecimal() or not owner:
            continue
        source_url = f'https://www.flickr.com/photos/{quote(owner, safe="")}/{pid}/'
        preview_url = item.get('url_q') or item.get('url_m') or ''
        image_url = item.get('url_m') or item.get('url_q') or ''
        if not valid_https(preview_url, {'live.staticflickr.com'}):
            continue
        if not valid_https(image_url, {'live.staticflickr.com'}):
            continue
        license_name, license_url = lic
        candidates.append({
            'provider': 'flickr', 'provider_id': pid,
            'title': clean_text(item.get('title'), 250),
            'preview_url': preview_url, 'image_url': image_url,
            'source_url': source_url,
            'credit': clean_text(item.get('ownername'), 300),
            'license': license_name, 'license_url': license_url,
            'license_supported': 'yes' if license_name in SUPPORTED else 'no',
            'identity_status': 'UNVERIFIED — Flickr name/location are not proof',
        })
    return candidates


def load_rows():
    if not CSV_PATH.exists():
        return []
    with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or set(reader.fieldnames) != set(FIELDS):
            raise CommandError('Multi-source CSV columns changed; refusing to replace original.')
        rows = list(reader)
    seen = set()
    for row in rows:
        pid = row.get('place_id') or ''
        if not pid.isascii() or not pid.isdecimal() or row.get('city_id') != str(CITY_ID):
            raise CommandError('CSV contains non-Kabankalan or malformed place ID; no changes.')
        if row.get('provider') not in ('openverse', 'flickr'):
            raise CommandError('CSV contains an unexpected provider; no changes.')
        key = pid, row.get('source_url')
        if not valid_https(row.get('source_url') or '') or key in seen:
            raise CommandError('CSV contains invalid/duplicate source links; no changes.')
        seen.add(key)
    return rows


def save_rows(rows):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = CSV_PATH.with_suffix('.csv.tmp')
    with temp.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: commons_bulk.safe_cell(row.get(key, '')) for key in FIELDS})
    os.replace(temp, CSV_PATH)


def load_status():
    if not STATUS_PATH.exists():
        return {}
    try:
        with STATUS_PATH.open('r', encoding='utf-8') as stream:
            obj = json.load(stream)
        if (not isinstance(obj, dict) or obj.get('schema') != SCHEMA
                or not isinstance(obj.get('attempts'), dict)):
            raise ValueError('Unexpected multi-source status file schema')
        return obj['attempts']
    except (ValueError, OSError) as exc:
        raise CommandError('Multi-source search status needs review: ' + str(exc)) from exc


def save_status(attempts):
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATUS_PATH.with_suffix('.json.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump({'schema': SCHEMA, 'attempts': attempts}, stream,
                  ensure_ascii=False, indent=2)
    os.replace(temp, STATUS_PATH)


def get_kabankalan_places():
    city = City.objects.filter(pk=CITY_ID).first()
    if city is None or city.name.strip().casefold() != 'kabankalan':
        raise CommandError('City ID 2 is not Kabankalan; refusing operation.')
    return list(Place.objects.filter(city_id=CITY_ID).order_by('pk'))


def esc(value):
    return html.escape(str(value or ''), quote=True)


def make_gallery(places, external_rows, commons_rows):
    """Create a static read-only gallery, joining ONLY city 2 by Place ID."""
    by_id = {}
    for row in external_rows:
        by_id.setdefault(row['place_id'], []).append(row)
    for row in commons_rows:
        if row.get('city_id') != str(CITY_ID):
            continue
        by_id.setdefault(row.get('place_id'), []).append({
            **row,
            'provider': 'commons',
            'title': row.get('file_title') or '',
            'preview_url': row.get('image_url') or '',
            'identity_status': 'UNVERIFIED — Commons candidate also needs human review',
            'license_supported': 'yes' if row.get('license') in SUPPORTED else 'no',
        })
    missing = sum(not (p.cover_image or p.cover_image_url) for p in places)
    out = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width,initial-scale=1">',
        '<title>ExploreAnywhere | Kabankalan Multi-Source Photo Review</title>',
        '<style>body{font:15px system-ui,sans-serif;max-width:1250px;',
        'margin:30px auto;padding:0 18px;background:#f6f8fc;color:#172d4b}',
        '.note{background:#fff;border:1px solid #d8e1ed;padding:14px;border-radius:9px}',
        '.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:16px}',
        'article{background:#fff;border:1px solid #d8e1ed;border-radius:11px;overflow:hidden}',
        'article img{width:100%;height:175px;object-fit:cover;background:#e9eff8}',
        '.body{padding:13px}small{color:#53677e}a{color:#1556a4}p{overflow-wrap:anywhere}',
        '.pill{display:inline-block;padding:4px 8px;background:#edf1f6;border-radius:6px}',
        '</style></head><body><h1>Kabankalan multi-source photo candidates</h1>',
        f'<p>{len(places)} Kabankalan places · {missing} missing covers · ',
        f'{len(external_rows)} Openverse/Flickr leads · ',
        f'{sum(1 for r in commons_rows if r.get("city_id") == str(CITY_ID))} Commons leads</p>',
        '<p class="note"><b>Every result is UNVERIFIED.</b> Similar business names, ',
        'search relevance, and location labels do not prove photo identity. ',
        'Check the original page, creator and license before using a photograph. ',
        'Flickr CC BY/SA 2.0 photos are legitimate CC licenses but are <b>not ',
        'supported by the current import policy</b>. This dashboard cannot ',
        'approve, download or import photos; old Commons importer remains Commons-only.</p>',
        '<div class="grid">',
    ]
    place_map = {str(p.pk): p for p in places}
    shown = 0
    for pid, entries in sorted(by_id.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else -1):
        place = place_map.get(pid)
        if place is None or (place.cover_image or place.cover_image_url):
            continue
        for row in entries:
            source = row.get('source_url') or ''
            preview = row.get('preview_url') or ''
            if not valid_https(source):
                continue
            shown += 1
            out.append('<article>')
            if valid_https(preview):
                out.append('<img loading="lazy" referrerpolicy="no-referrer" '
                           f'src="{esc(preview)}" alt="Unverified candidate image">')
            out.append('<div class="body">'
                       f'<small>ID {esc(pid)} · {esc(row.get("provider"))}</small>'
                       f'<h3>{esc(place.title)}</h3>'
                       f'<p>{esc(row.get("title"))}</p>'
                       f'<p>Photographer: {esc(row.get("credit") or "Not supplied")}</p>'
                       f'<p>License: {esc(row.get("license"))} '
                       f'({"currently supported" if row.get("license_supported") == "yes" else "requires policy check"})</p>'
                       f'<p><a target="_blank" rel="noopener noreferrer" '
                       f'href="{esc(source)}">Review original source</a></p>'
                       f'<small>{esc(row.get("identity_status"))}</small>'
                       '</div></article>')
    if not shown:
        out.append('<p>No verified or unverified leads to display yet.</p>')
    out.append('</div></body></html>')
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = HTML_PATH.with_suffix('.html.tmp')
    temp.write_text(''.join(out), encoding='utf-8')
    os.replace(temp, HTML_PATH)
    return shown


def source_names(value):
    sources = SOURCES if value.strip().lower() == 'all' else tuple(
        v.strip().lower() for v in value.split(',') if v.strip()
    )
    if not sources or len(sources) != len(set(sources)) or set(sources) - set(SOURCES):
        raise CommandError('Use --sources all or a comma-separated subset: openverse,flickr,commons')
    return sources


def safe_error(exc):
    """Do not leak Flickr API keys or full signed URLs into the terminal."""
    if isinstance(exc, HTTPError):
        return f'HTTP {exc.code}'
    if isinstance(exc, URLError):
        return 'network/TLS error (' + type(exc.reason).__name__ + ')'
    return type(exc).__name__ + ': ' + clean_text(exc, 130)


class Command(BaseCommand):
    help = ('Phase 6P.8: Kabankalan-only Openverse/Flickr discovery plus existing '
            'Commons collector; no MySQL writes or automatic photo approval.')

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--discover', action='store_true', help='Search the selected sources')
        group.add_argument('--status', action='store_true', help='Read-only candidate counts')
        group.add_argument('--gallery', action='store_true', help='Regenerate merged HTML review gallery')
        parser.add_argument('--city-id', type=int, default=CITY_ID,
                            help='Must be 2 (Kabankalan). Other cities are never queried')
        parser.add_argument('--offset', type=int, default=0,
                            help='Offset in stable published-first inventory (default 0)')
        parser.add_argument('--limit', type=int, default=5,
                            help='Places in this discovery window, 1–20')
        parser.add_argument('--per-query', type=int, default=2,
                            help='Maximum candidates per provider query, 1–5')
        parser.add_argument('--sources', default='all',
                            help='all or openverse,flickr,commons (comma-separated)')
        parser.add_argument('--rescan', action='store_true',
                            help='Repeat cached API queries; existing reviews preserved')

    def handle(self, *args, **opts):
        if opts['city_id'] != CITY_ID:
            raise CommandError('Only --city-id 2 (Kabankalan) is supported.')
        if not 1 <= opts['limit'] <= 20 or opts['offset'] < 0 or not 1 <= opts['per_query'] <= 5:
            raise CommandError('Use --limit 1–20, --offset >= 0, --per-query 1–5.')
        if opts['rescan'] and not opts['discover']:
            raise CommandError('--rescan only works with --discover.')
        sources = source_names(opts['sources'])
        places = get_kabankalan_places()
        rows = load_rows()
        if opts['status']:
            common = [r for r in commons_bulk.load_rows() if r.get('city_id') == str(CITY_ID)]
            self.stdout.write(f'KABANKALAN: {len(places)} places; '
                              f'{sum(not (p.cover_image or p.cover_image_url) for p in places)} missing covers. '
                              f'Openverse/Flickr leads: {len(rows)}; Commons leads: {len(common)}.')
            self.stdout.write(f'External manual review decisions: '
                              f'{sum((r.get("review_decision") or "").lower() == "approve" for r in rows)} '
                              'marked approve (NOT importable by Commons-only importer).')
            self.stdout.write('READ ONLY. Database unchanged.')
            return
        if opts['gallery']:
            common = commons_bulk.load_rows()
            shown = make_gallery(places, rows, common)
            self.stdout.write(f'GALLERY READY: {shown} unverified leads. {HTML_PATH}')
            self.stdout.write('Database unchanged.')
            return
        self.discover(places, rows, sources, opts)

    def discover(self, places, rows, sources, opts):
        agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
        if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT with a real contact email.')
        try:
            import truststore
        except ImportError as exc:
            raise CommandError('Install truststore: python -m pip install truststore') from exc
        truststore.inject_into_ssl()
        self.stdout.write('Secure HTTPS verification: Windows/system truststore enabled.')
        ordered = sorted(places, key=lambda p: (not (p.is_active and p.is_verified), p.pk))
        batch = ordered[opts['offset']:opts['offset'] + opts['limit']]
        targets = [p for p in batch if not (p.cover_image or p.cover_image_url)]
        self.stdout.write(f'KABANKALAN ONLY: {len(targets)} missing-cover targets in '
                          f'window {opts["offset"]}–{opts["offset"]+opts["limit"]-1} '
                          f'of {len(ordered)}. DATABASE READ ONLY.')
        api_sources = tuple(s for s in sources if s in ('openverse', 'flickr'))
        api_key = os.environ.get('EXPLOREANYWHERE_FLICKR_API_KEY', '').strip()
        if 'flickr' in api_sources and not api_key:
            if api_sources == ('flickr',):
                raise CommandError('Flickr API requires EXPLOREANYWHERE_FLICKR_API_KEY.')
            self.stdout.write('Flickr SKIPPED: no API key. Openverse may include Flickr-indexed photos.')
            api_sources = tuple(s for s in api_sources if s != 'flickr')
        status = load_status()
        seen = {(r['place_id'], r['source_url']) for r in rows}
        existing_approved = {r['place_id'] for r in rows
                             if (r.get('review_decision') or '').strip().lower() == 'approve'}
        added = 0
        queries = 0
        errors = 0
        skipped = 0
        csv_backup = False
        for place in targets:
            pid = str(place.pk)
            for source in api_sources:
                key = source + ':' + pid
                old = status.get(key)
                if (not opts['rescan'] and isinstance(old, dict)
                        and old.get('slug') == place.slug
                        and old.get('search_version') == SEARCH_VERSION
                        and old.get('result') in ('leads', 'no_leads')):
                    skipped += 1
                    continue
                if pid in existing_approved:
                    skipped += 1
                    continue  # Never interfere with any prior decision.
                source_count = 0
                source_error = False
                for query in photo_queries(place.title):
                    queries += 1
                    try:
                        found = (openverse_candidates(query, opts['per_query'], agent)
                                 if source == 'openverse' else
                                 flickr_candidates(query, opts['per_query'], agent, api_key))
                        self.stdout.write(f'  [{source}] {place.title} ({pid}): '
                                          f'{len(found)} leads for {query!r}')
                        for item in found:
                            identity = (pid, item['source_url'])
                            if identity in seen:
                                continue
                            seen.add(identity)
                            source_count += 1
                            rows.append({
                                'place_id': pid, 'city_id': str(CITY_ID),
                                'place_slug': place.slug,
                                'place_name': commons_bulk.safe_cell(place.title),
                                'latitude': str(place.latitude or ''),
                                'longitude': str(place.longitude or ''),
                                'search_query': query,
                                **item,
                                **{f: '' for f in REVIEW_FIELDS},
                            })
                            added += 1
                        if source_count and not csv_backup and CSV_PATH.exists():
                            backup = CSV_PATH.with_name(
                                CSV_PATH.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
                            shutil.copy2(CSV_PATH, backup)
                            csv_backup = True
                            self.stdout.write('Multi-source review CSV backup: ' + str(backup))
                        if source_count:
                            save_rows(rows)  # Save candidate leads as soon as found.
                    except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError,
                            UnicodeError, json.JSONDecodeError) as exc:
                        source_error = True
                        errors += 1
                        self.stdout.write(f'  [{source}] API WARNING: {safe_error(exc)}')
                    time.sleep(1.0)
                status[key] = {
                    'slug': place.slug, 'search_version': SEARCH_VERSION,
                    'result': 'retry' if source_error else ('leads' if source_count else 'no_leads'),
                    'checked_utc': datetime.now(timezone.utc).isoformat(),
                }
                save_status(status)
        if 'commons' in sources:
            # The original Commons importer requires exact Commons-hosted links.
            # Reuse its established discovery/cache/CSV instead of contaminating
            # its import CSV with Openverse or Flickr remote image URLs.
            self.stdout.write('Running established Kabankalan-only Commons collector...')
            cmd_args = [
                '--discover', '--city-id', str(CITY_ID), '--published-first',
                '--offset', str(opts['offset']), '--limit', str(opts['limit']),
                '--per-query', str(opts['per_query']),
            ]
            if opts['rescan']:
                cmd_args.append('--rescan')
            call_command('phase6p_kabankalan_photos', *cmd_args)
        if not CSV_PATH.exists():
            save_rows(rows)  # Empty CSV with correct headings is still useful.
        common = commons_bulk.load_rows()
        shown = make_gallery(places, rows, common)
        self.stdout.write(self.style.SUCCESS(
            f'MULTI-SOURCE COMPLETE: {queries} external API queries, {added} new '
            f'Openverse/Flickr leads, {skipped} cached skips, {errors} API warnings.'))
        self.stdout.write(f'REVIEW CSV: {CSV_PATH}\nGALLERY: {HTML_PATH} '
                          f'({shown} unverified leads total including Commons).')
        self.stdout.write('Database unchanged. NO automatic approvals or imports.')
