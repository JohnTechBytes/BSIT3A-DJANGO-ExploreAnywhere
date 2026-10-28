"""Phase 6O.2: opt-in Commons name search, strictly for *review-only* leads.

This command reads Kabankalan Place records, queries Wikimedia Commons, and writes
its own separate CSV/HTML reports. It NEVER writes to the database and NEVER
changes the existing Phase 6O CSV/gallery or any approval workflow.

Run after placing under apps/places/management/commands/:
    python manage.py phase6o_search_commons --limit 5
"""
import csv
import html
import os
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.cities.models import City
from apps.places.models import Place
from apps.places.management.commands.phase6o_business_photos import (
    CITY_ID, LICENSES, clean_text, error_detail, network_json, safe_cell,
    trusted_https,
)

REVIEW_DIR = Path(settings.BASE_DIR) / 'phase6_photo_review'
OUTPUT_CSV = REVIEW_DIR / 'kabankalan_commons_search_candidates.csv'
OUTPUT_HTML = REVIEW_DIR / 'kabankalan_commons_search_gallery.html'
STARTER_PLACES = (
    'Kabankalan Plaza', 'Mag Aso Falls', 'Maronggues Hill',
    'Mount Nai-guin', 'Amyan Hill',
)
# Aliases only broaden discovery; they never constitute identity verification.
ALIASES = {'Mag Aso Falls': ('Mag-aso Falls',)}
COLUMNS = (
    'place_id', 'place_name', 'place_slug', 'search_query', 'file_title',
    'image_url', 'source_url', 'credit', 'license', 'license_url',
    'match_status', 'review_decision', 'identity_checked', 'rights_checked',
    'review_notes',
)
REVIEW_FIELDS = ('review_decision', 'identity_checked', 'rights_checked', 'review_notes')


def searches_for(name):
    """Location-qualified queries, never a locationless general image query."""
    variants = (name,) + ALIASES.get(name, ())
    queries = []
    for variant in variants:
        cleaned = variant.replace('"', '').strip()[:100]
        if cleaned:
            queries.append(f'"{cleaned}" Kabankalan')
            queries.append(f'"{cleaned}" "Negros Occidental"')
    return tuple(dict.fromkeys(queries))


def commons_search(query, agent, per_query):
    """Return Commons file candidates. A search result is NEVER proof of identity."""
    params = urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search',
        'gsrsearch': query, 'gsrnamespace': 6, 'gsrlimit': per_query,
        'prop': 'imageinfo', 'iiprop': 'url|extmetadata|mime', 'iiurlwidth': 720,
    })
    payload = network_json('https://commons.wikimedia.org/w/api.php?' + params, agent)
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
                    'SEARCH LEAD ONLY — identity unverified; license metadata present'
                    if license_check else
                    'SEARCH LEAD ONLY — identity and rights require review'
                ),
            })
    return result


def load_existing():
    if not OUTPUT_CSV.exists():
        return []
    with OUTPUT_CSV.open('r', encoding='utf-8-sig', newline='') as fh:
        reader = csv.DictReader(fh)
        if set(COLUMNS) - set(reader.fieldnames or ()):
            raise CommandError('Existing search CSV format differs. Back it up and review it first.')
        rows = list(reader)
    keys = set()
    for row in rows:
        key = (row['place_id'], row['source_url'])
        if key in keys:
            raise CommandError('Duplicate entries found in the existing search CSV.')
        keys.add(key)
    return rows


def save_csv(rows):
    REVIEW_DIR.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT_CSV.with_suffix('.csv.tmp')
    with temporary.open('w', encoding='utf-8-sig', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction='ignore')
        writer.writeheader()
        for row in rows:
            writer.writerow({key: safe_cell(row.get(key, '')) for key in COLUMNS})
    os.replace(temporary, OUTPUT_CSV)


def create_gallery(rows):
    parts = [
        '<!doctype html><html lang="en"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<title>ExploreAnywhere — Commons search leads</title>',
        '<style>body{font:15px system-ui,sans-serif;background:#f5f7fb;color:#19283d;',
        'max-width:1300px;margin:0 auto;padding:24px}.grid{display:grid;',
        'grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:16px}',
        'article{background:white;border:1px solid #dae1ed;border-radius:12px;',
        'overflow:hidden}article img{width:100%;height:180px;object-fit:cover;',
        'background:#e8edf4}article div{padding:14px}h2{font-size:17px}',
        'p{overflow-wrap:anywhere}a{color:#1555af}</style></head><body>',
        '<h1>Commons search leads — Kabankalan</h1>',
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
            f'alt="Unverified search lead for {e("place_name")}"><div>'
            f'<h2>{e("place_name")}</h2>'
            f'<p>{e("file_title")}</p>'
            f'<p>{e("search_query")}</p>'
            f'<p>{e("license")} — {e("credit")}</p>'
            f'<p>{e("match_status")}</p>'
            f'<p><a href="{e("source_url")}" target="_blank" '
            f'rel="noopener noreferrer">View original on Commons</a></p>'
            '</div></article>'
        )
    parts.extend(['</main></body></html>'])
    OUTPUT_HTML.write_text(''.join(parts), encoding='utf-8')


class Command(BaseCommand):
    help = 'Find unverified Wikimedia Commons leads; separate, read-only Phase 6O.2 search.'

    def add_arguments(self, parser):
        parser.add_argument('--names', default=','.join(STARTER_PLACES),
                            help='Comma-separated exact Kabankalan place titles')
        parser.add_argument('--limit', type=int, default=5,
                            help='Maximum selected places (1–10)')
        parser.add_argument('--per-query', type=int, default=5,
                            help='Maximum candidate results for each search (1–5)')

    def handle(self, *args, **opts):
        if not 1 <= opts['limit'] <= 10 or not 1 <= opts['per_query'] <= 5:
            raise CommandError('--limit must be 1–10 and --per-query 1–5')
        city = City.objects.filter(pk=CITY_ID).first()
        if city is None or city.name.strip().casefold() != 'kabankalan':
            raise CommandError('City 2 is not Kabankalan. No action taken.')
        agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
        if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT with real contact email.')
        names = list(dict.fromkeys(x.strip() for x in opts['names'].split(',') if x.strip()))
        if not names:
            raise CommandError('No place names provided.')
        if len(names) > opts['limit']:
            self.stdout.write(f'Inspecting first {opts["limit"]} of {len(names)} requested places.')
        rows = load_existing()
        seen = {(r['place_id'], r['source_url']) for r in rows}
        added = 0
        for name in names[:opts['limit']]:
            matches = list(Place.objects.filter(city_id=CITY_ID, title__iexact=name)[:2])
            if len(matches) != 1:
                self.stdout.write(f'SKIP {name}: expected one exact place, found {len(matches)}.')
                continue
            place = matches[0]
            if place.cover_image or place.cover_image_url:
                self.stdout.write(f'SKIP {name}: existing cover preserved.')
                continue
            self.stdout.write(f'SEARCH {place.title} (place {place.pk})')
            for query in searches_for(place.title):
                try:
                    candidates = commons_search(query, agent, opts['per_query'])
                except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                    self.stdout.write(f'  ERROR: {error_detail(exc)}')
                    time.sleep(0.8)
                    continue
                for candidate in candidates:
                    key = (str(place.pk), candidate['source_url'])
                    if key in seen:
                        continue  # Keep previous review work unchanged.
                    seen.add(key)
                    rows.append({
                        'place_id': str(place.pk), 'place_name': place.title,
                        'place_slug': place.slug, 'search_query': query,
                        **candidate,
                        **{field: '' for field in REVIEW_FIELDS},
                    })
                    added += 1
                self.stdout.write(f'  Query {query!r}: {len(candidates)} search leads')
                save_csv(rows)  # Checkpoint after each query; never touches original CSV.
                time.sleep(0.8)
        save_csv(rows)
        create_gallery(rows)
        self.stdout.write(self.style.SUCCESS(
            f'SEARCH COMPLETE: {added} new leads, {len(rows)} retained in review report. '
            'Database and original Phase 6O review files unchanged.'
        ))
        self.stdout.write(f'CSV: {OUTPUT_CSV}\nGALLERY: {OUTPUT_HTML}')
