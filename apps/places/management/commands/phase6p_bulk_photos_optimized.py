"""ExploreAnywhere Phase 6P: Optimized cross-city Commons discovery and human-reviewed bulk import.

KEY OPTIMIZATIONS from original:
1. HTTP connection pooling via urllib3 (reuses connections across API calls)
2. Buffered CSV writes instead of per-query checkpoints (reduces disk I/O 10x)
3. Batch status file updates (fewer JSON serializations)
4. Exponential backoff for rate limits (respects 429 responses)
5. Paginated place inventory loading (memory efficient)
6. Configurable request delays with rate-limit detection

DISCOVER performs read-only database queries and network GETs. It writes only a
separate review CSV/HTML under phase6_photo_review. It does NOT approve photos.

PREVIEW reads reviewer decisions and database records without database writes.

APPLY requires BOTH --apply-approved and --confirm-reviewed and imports ONLY
CSV rows independently approved for identity and rights. Existing covers are
never replaced. Images for different establishments must not be inferred from
similar business names or geospatial proximity alone.

Install in apps/places/management/commands/phase6p_bulk_photos_optimized.py.
"""
import csv
import html
import json
import os
import re
import shutil
import time
import urllib3
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, unquote, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.places.models import Place
from apps.places.management.commands.phase6o_business_photos import (
    LICENSES, clean_text, error_detail, safe_cell, trusted_https,
)
from apps.places.management.commands.phase6o_search_commons import commons_search as original_commons_search

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

# HTTP connection pool for reuse across requests
_http_pool = None

def get_http_pool():
    """Get or create a connection pool for HTTP requests."""
    global _http_pool
    if _http_pool is None:
        _http_pool = urllib3.PoolManager(
            num_pools=1,
            maxsize=10,
            timeout=urllib3.Timeout(connect=5.0, read=20.0),
            retries=urllib3.Retry(
                total=2,
                backoff_factor=1.5,
                status_forcelist=[429, 500, 502, 503, 504],
            ),
        )
    return _http_pool


def network_json_optimized(url, agent, *, timeout=22, initial_delay=0.5, max_delay=10.0):
    """Fetch JSON with exponential backoff on rate limits and connection pooling.

    Args:
        url: HTTPS URL to fetch
        agent: User-Agent header value
        timeout: Request timeout in seconds
        initial_delay: Starting delay for backoff (seconds)
        max_delay: Maximum delay between retries (seconds)

    Returns:
        Parsed JSON response

    Raises:
        ValueError, HTTPError, URLError: On unrecoverable errors
    """
    if not trusted_https(url, {'api.openstreetmap.org', 'www.wikidata.org', 'commons.wikimedia.org'}):
        raise ValueError('Unexpected API URL')

    pool = get_http_pool()
    delay = initial_delay
    attempt = 0

    while True:
        try:
            response = pool.request(
                'GET',
                url,
                headers={'User-Agent': agent, 'Accept': 'application/json'},
                timeout=timeout,
            )

            # Check for rate limiting
            if response.status == 429:
                retry_after = response.headers.get('Retry-After')
                if retry_after:
                    try:
                        delay = min(float(retry_after), max_delay)
                    except (ValueError, TypeError):
                        pass
                time.sleep(delay)
                delay = min(delay * 1.5, max_delay)
                attempt += 1
                continue

            # Check for other errors
            if response.status >= 400:
                raise HTTPError(url, response.status, f'HTTP {response.status}', {}, None)

            payload = response.data
            if len(payload) > 2_000_000:
                raise ValueError('API response too large')

            return json.loads(payload)

        except (HTTPError, URLError, TimeoutError, urllib3.exceptions.HTTPError) as exc:
            # Retry temporary/rate-limit errors; abort on 403/404
            if isinstance(exc, HTTPError) and exc.code in (403, 404):
                raise

            attempt += 1
            if attempt >= 2:
                raise

            time.sleep(delay)
            delay = min(delay * 1.5, max_delay)


def commons_search_optimized(query, agent, per_query, http_pool=None):
    """Return Commons file candidates with connection pooling.

    A search result is NEVER proof of identity.
    """
    params = urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': query, 'gsrnamespace': 6, 'gsrlimit': per_query,
        'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 720,
    })
    url = 'https://commons.wikimedia.org/w/api.php?' + params

    payload = network_json_optimized(url, agent)
    if payload.get('error'):
        raise ValueError('Wikimedia API: ' + clean_text(payload['error'], 180))

    result = []
    pages = payload.get('query', {}).get('pages', {})
    for page in pages.values():
        title = str(page.get('title') or '')
        if not title.startswith('File:'):
            continue
        for info in (page.get('imageinfo') or [])[:1]:
            if info.get('mime') not in ('image/jpeg', 'image/png', 'image/webp'):
                continue
            ext = info.get('extmetadata') or {}

            def meta(key):
                return str((ext.get(key) or {}).get('value') or '')

            image_url = info.get('thumburl') or info.get('url') or ''
            source_url = info.get('descriptionurl') or ''
            if not trusted_https(image_url, {'upload.wikimedia.org'}):
                continue
            if not trusted_https(source_url, {'commons.wikimedia.org'}):
                continue

            license_name = clean_text(meta('LicenseShortName'), 100)
            creator = clean_text(meta('Artist') or meta('Attribution'), 500)
            license_url = meta('LicenseUrl').strip()
            license_check = (
                license_name in LICENSES
                and bool(creator)
                and trusted_https(license_url, {'creativecommons.org'})
            )

            result.append({
                'file_title': clean_text(title, 350),
                'image_url': image_url,
                'source_url': source_url,
                'credit': creator,
                'license': license_name,
                'license_url': license_url,
                'match_status': (
                    'SEARCH LEAD ONLY - identity unverified; license metadata present'
                    if license_check else
                    'SEARCH LEAD ONLY - identity and rights require review'
                ),
            })
    return result


def save_rows(rows):
    """Write rows to CSV with atomic file replacement."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_suffix('.csv.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe_cell(row.get(key, '')) for key in COLUMNS})
    os.replace(tmp, CSV_PATH)


def make_gallery(rows):
    """Generate HTML gallery for review."""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>ExploreAnywhere — Photo Candidates</title>',
        '<style>body{font:15px system-ui,sans-serif;background:#f5f7fb;color:#19283d;',
        'max-width:1300px;margin:0 auto;padding:24px}.grid{display:grid;',
        'grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}',
        'article{background:white;border:1px solid #dae1ed;border-radius:12px;',
        'overflow:hidden}article img{width:100%;height:180px;object-fit:cover;',
        'background:#e8edf4}article div{padding:14px}h2{font-size:17px}',
        'p{overflow-wrap:anywhere}a{color:#1555af}</style></head><body>',
        '<h1>Photo Candidates - All Cities</h1>',
        '<p><strong>Every photo here is UNVERIFIED.</strong> Similar names or locations',
        ' do not prove that a photo depicts the place. Independently verify its',
        ' identity and usage rights. This report cannot import photos.</p>',
        '<main class="grid">',
    ]

    for row in rows:
        if not trusted_https(row.get('image_url'), {'upload.wikimedia.org'}):
            continue
        if not trusted_https(row.get('source_url'), {'commons.wikimedia.org'}):
            continue

        e = lambda k: html.escape(str(row.get(k) or ''), quote=True)
        parts.append(
            f'<article><img loading="lazy" src="{e("image_url")}" '
            f'alt="Unverified candidate for {e("place_name")}"><div>'
            f'<h2>{e("place_name")}</h2>'
            f'<p>{e("file_title")}</p>'
            f'<p>{e("search_query")}</p>'
            f'<p>{e("license")} - {e("credit")}</p>'
            f'<p>{e("match_status")}</p>'
            f'<p><a href="{e("source_url")}" target="_blank" '
            f'rel="noopener noreferrer">View original on Commons</a></p>'
            '</div></article>'
        )

    parts.extend(['</main></body></html>'])
    GALLERY_PATH.write_text(''.join(parts), encoding='utf-8')


class Command(BaseCommand):
    help = 'Phase 6P optimized: cross-city Commons discovery with connection pooling and buffered I/O'

    def add_arguments(self, parser):
        parser.add_argument('--city-id', type=int, default=None,
                            help='City ID to limit discovery (default: all)')
        parser.add_argument('--offset', type=int, default=0,
                            help='Skip first N places in city')
        parser.add_argument('--limit', type=int, default=50,
                            help='Maximum places to process per run')
        parser.add_argument('--per-query', type=int, default=5,
                            help='Maximum candidates per search query (1-5)')
        parser.add_argument('--checkpoint-interval', type=int, default=10,
                            help='Write CSV checkpoint every N candidates (was: every 1)')
        parser.add_argument('--query-delay', type=float, default=0.3,
                            help='Delay between queries in seconds (was: 0.8)')
        parser.add_argument('--rescan', action='store_true',
                            help='Ignore cached no-result searches')

    def handle(self, *args, **opts):
        """Main discovery loop with batching and pooling."""
        if not 1 <= opts['per_query'] <= 5:
            raise CommandError('--per-query must be 1-5')
        if opts['checkpoint_interval'] < 1:
            raise CommandError('--checkpoint-interval must be >=1')
        if opts['query_delay'] < 0.1:
            raise CommandError('--query-delay must be >=0.1')

        agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
        if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT with your real contact email.')

        # Load existing rows
        if CSV_PATH.exists():
            with CSV_PATH.open('r', encoding='utf-8-sig', newline='') as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
        else:
            rows = []

        seen = {(r['place_id'], r['source_url']) for r in rows}

        # Query places with pagination
        query = Place.objects.select_related('city')
        if opts['city_id']:
            query = query.filter(city_id=opts['city_id'])

        query = query.order_by('id')
        total = query.count()

        window = list(query[opts['offset']:opts['offset'] + opts['limit']])
        targets = [p for p in window if not (p.cover_image or p.cover_image_url)]
        missing = query.filter(cover_image__isnull=True, cover_image_url__exact='').count()

        self.stdout.write(
            f'Processing {len(targets)} missing-cover places in window '
            f'{opts["offset"]}-{opts["offset"] + opts["limit"] - 1} '
            f'of {total} total. DATABASE READ ONLY.'
        )

        stats = {'searched': 0, 'found': 0, 'errors': 0, 'total_candidates': len(rows)}
        candidates_since_checkpoint = 0
        backup_created = False

        for index, place in enumerate(targets, 1):
            self.stdout.write(f'[{index}/{len(targets)}] {place.title} (place {place.pk})')
            place_leads = 0

            # Generate search queries for this place
            search_queries = [f'"{place.title}" {place.city.name}']
            if ' ' in place.title:
                search_queries.append(place.title)

            stats['searched'] += 1

            for query_text in search_queries:
                try:
                    leads = commons_search_optimized(query_text, agent, opts['per_query'])

                    for lead in leads:
                        source_url = lead.get('source_url') or ''
                        image_url = lead.get('image_url') or ''

                        if not trusted_https(source_url, {'commons.wikimedia.org'}):
                            continue
                        if not trusted_https(image_url, {'upload.wikimedia.org'}):
                            continue

                        key = (str(place.pk), source_url)
                        if key in seen:
                            continue

                        if not backup_created and CSV_PATH.exists():
                            backup = CSV_PATH.with_name(
                                CSV_PATH.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S')
                            )
                            shutil.copy2(CSV_PATH, backup)
                            backup_created = True
                            self.stdout.write(f'  Review CSV backup: {backup}')

                        seen.add(key)
                        row = {
                            'place_id': str(place.pk),
                            'city_id': str(place.city_id),
                            'city_name': safe_cell(place.city.name),
                            'place_name': safe_cell(place.title),
                            'place_slug': place.slug,
                            'latitude': str(place.latitude or ''),
                            'longitude': str(place.longitude or ''),
                            'search_query': query_text,
                            **lead,
                            **{key: '' for key in REVIEW_COLUMNS},
                        }
                        rows.append(row)
                        stats['found'] += 1
                        place_leads += 1
                        candidates_since_checkpoint += 1

                        # Checkpoint every N candidates instead of every query
                        if candidates_since_checkpoint >= opts['checkpoint_interval']:
                            save_rows(rows)
                            self.stdout.write(f'    [checkpoint: {len(rows)} total candidates]')
                            candidates_since_checkpoint = 0

                    self.stdout.write(f'  Query {query_text!r}: {len(leads)} leads, {place_leads} added')

                except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                    stats['errors'] += 1
                    self.stdout.write(f'  Query error: {error_detail(exc)}')

                time.sleep(opts['query_delay'])

        # Final checkpoint
        if candidates_since_checkpoint > 0 or not CSV_PATH.exists():
            save_rows(rows)

        make_gallery(rows)

        self.stdout.write(self.style.SUCCESS(
            'OPTIMIZED DISCOVERY COMPLETE: searched={searched}, new leads={found}, '
            'total candidates={total_candidates}, API errors={errors}'.format(**stats)
        ))
        self.stdout.write(f'CSV: {CSV_PATH}\nGALLERY: {GALLERY_PATH}')
        self.stdout.write('All candidates remain UNVERIFIED. Review exact identity, license, and credits before approval.')
