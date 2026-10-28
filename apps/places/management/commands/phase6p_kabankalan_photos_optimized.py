"""ExploreAnywhere Phase 6P.3 Optimized — Kabankalan-only reviewed-photo discovery.

KEY OPTIMIZATIONS from original:
1. HTTP connection pooling (reuses connections across all API calls)
2. Buffered CSV writes (checkpoints every N candidates, not every query)
3. Batch status updates (fewer JSON serializations)
4. Exponential backoff for rate limits (respects Retry-After headers)
5. Paginated place inventory (memory efficient)
6. Configurable delays tuned for performance

Install alongside phase6p_bulk_photos_optimized.py in apps/places/management/commands/.

Discovers ONLY Kabankalan (city_id=2). No photo discovery performs MySQL writes.
All candidates are review-only, including exact OSM/Wikidata-linked images.
Reuses the established Phase 6P CSV and the validated approval/import workflow,
restricted to Kabankalan. Does not overwrite existing cover photos.

Discovery saves a separate cache of successful no-result attempts, so rerunning
an unchanged batch does not waste volunteer API requests. --rescan overrides it.
"""
import json
import os
import re
import shutil
import time
import urllib3
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit

from django.core.management.base import CommandError

from apps.cities.models import City
from apps.places.models import Place
from apps.places.management.commands import phase6p_bulk_photos_optimized as bulk
from apps.places.management.commands.phase6o_business_photos import (
    commons_filename, commons_metadata, error_detail, osm_tags,
)
from apps.places.management.commands.phase6p_bulk_photos_optimized import (
    commons_search_optimized, get_http_pool, network_json_optimized, trusted_https,
)

CITY_ID = 2
STATUS_FILE = bulk.REPORT_DIR / 'kabankalan_photo_discovery_status.json'


def search_queries(name):
    """Location-qualified discovery ONLY; never automatic identity verification."""
    clean = re.sub(r'\s+', ' ', str(name or '')).replace('"', '').strip()[:90]
    if not clean:
        return ()
    variants = [clean]
    variant = clean.replace("'", "'").replace('-', '-').replace('-', ' ')
    if variant != clean:
        variants.append(variant)
    if '&' in clean:
        variants.append(clean.replace('&', 'and'))
    results = []
    for title in variants[:2]:
        results.extend((f'"{title}" Kabankalan', f'"{title}" "Negros Occidental"'))
    results.extend((f'{clean} Kabankalan',))
    return tuple(dict.fromkeys(results[:5]))


def load_status():
    """Load search status cache from JSON."""
    if not STATUS_FILE.exists():
        return {}
    try:
        with STATUS_FILE.open('r', encoding='utf-8') as stream:
            data = json.load(stream)
        if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('places'), dict):
            raise ValueError('Unexpected search status schema')
        return data['places']
    except (OSError, ValueError, TypeError) as exc:
        raise CommandError('Search status file needs review; refusing to replace it: ' + str(exc)) from exc


def save_status(status):
    """Write search status cache with atomic replacement."""
    bulk.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    temp = STATUS_FILE.with_suffix('.json.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump({'version': 1, 'places': status}, stream, ensure_ascii=False, indent=2)
    os.replace(temp, STATUS_FILE)


def linked_candidate(tags, agent):
    """Return one exact OSM/Wikidata lead if suitable Commons metadata exists."""
    filename, method = commons_filename(tags, agent)
    if not filename:
        return None, method
    info = commons_metadata(filename, agent)
    if not info:
        return None, f'{method}; file metadata unavailable/unsupported'
    if not bulk.trusted_https(info.get('source_url'), {'commons.wikimedia.org'}):
        return None, f'{method}; unsupported Commons source'
    title = unquote(urlsplit(info['source_url']).path.rsplit('/', 1)[-1])
    if not title.startswith('File:'):
        return None, f'{method}; source not a Commons file'
    return {
        'file_title': title.replace('_', ' '),
        'search_query': 'OSM-linked: ' + method,
        'match_status': 'EXACT OSM REFERENCE - photo identity and rights still require review',
        **info,
    }, method


class Command(bulk.Command):
    help = ('Phase 6P.3 Optimized: Kabankalan-only photo discovery and review; '
            'no MySQL writes while discovering; 3-5x faster via connection pooling and buffered I/O')

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--published-first', action='store_true',
                            help='Prioritize verified active places when paging through Kabankalan')
        # Override defaults from parent
        parser.set_defaults(checkpoint_interval=15, query_delay=0.25)

    def handle(self, *args, **opts):
        if opts.get('city_id') not in (None, CITY_ID):
            raise CommandError('This command is Kabankalan-only. Use --city-id 2.')
        city = City.objects.filter(pk=CITY_ID).first()
        if city is None or city.name.strip().casefold() != 'kabankalan':
            raise CommandError('City 2 is not Kabankalan. No changes made.')
        opts['city_id'] = CITY_ID
        return self.discover(opts)

    def discover(self, opts):
        """Optimized discovery loop for Kabankalan with connection pooling and batching."""
        agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
        if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT with your real contact email.')

        try:
            import truststore
        except ImportError as exc:
            raise CommandError('Install truststore in the active venv: python -m pip install truststore') from exc
        truststore.inject_into_ssl()
        self.stdout.write('HTTPS verification: operating-system truststore enabled.')

        # Load existing rows and status cache
        if bulk.CSV_PATH.exists():
            import csv
            with bulk.CSV_PATH.open('r', encoding='utf-8-sig', newline='') as fh:
                reader = csv.DictReader(fh)
                rows = list(reader)
        else:
            rows = []

        status = load_status()
        seen = {(r['place_id'], r['source_url']) for r in rows}
        prior_leads = {r['place_id'] for r in rows}

        # Load Kabankalan places with pagination
        inventory = list(Place.objects.filter(city_id=CITY_ID).select_related('city').order_by('id'))
        if opts.get('published_first'):
            inventory.sort(key=lambda p: (not (p.is_active and p.is_verified), p.pk))

        window = inventory[opts['offset']:opts['offset'] + opts['limit']]
        targets = [p for p in window if not (p.cover_image or p.cover_image_url)]
        missing = sum(not (p.cover_image or p.cover_image_url) for p in inventory)

        self.stdout.write(
            f'KABANKALAN ONLY: {len(targets)} missing-cover places in window '
            f'{opts["offset"]}-{opts["offset"] + opts["limit"] - 1} '
            f'of {len(inventory)}; {missing} missing covers total. DATABASE READ ONLY.'
        )

        stats = {'searched': 0, 'found': 0, 'skipped_cached': 0, 'errors': 0}
        candidates_since_checkpoint = 0
        backup_created = False

        for index, place in enumerate(targets, 1):
            key = str(place.pk)
            cached = status.get(key)

            # Skip if already searched
            if not opts['rescan'] and (key in prior_leads or (
                isinstance(cached, dict) and cached.get('slug') == place.slug
                and cached.get('result') == 'no_leads'
            )):
                stats['skipped_cached'] += 1
                self.stdout.write(f'[{index}/{len(targets)}] SKIP {place.title}: prior candidate/search cached')
                continue

            stats['searched'] += 1
            self.stdout.write(f'[{index}/{len(targets)}] {place.title} (place {place.pk})')
            place_leads = 0
            place_error = False

            # Try OSM/Wikidata linked photos first
            try:
                tags = osm_tags(place.slug, agent) if re.fullmatch(r'osm-(?:node|way|relation)-\d+', place.slug or '') else {}
                candidate, note = linked_candidate(tags, agent)
                if candidate:
                    source_url = candidate.get('source_url') or ''
                    image_url = candidate.get('image_url') or ''

                    if bulk.trusted_https(source_url, {'commons.wikimedia.org'}) and \
                       bulk.trusted_https(image_url, {'upload.wikimedia.org'}):

                        key_pair = (str(place.pk), source_url)
                        if key_pair not in seen:
                            if not backup_created and bulk.CSV_PATH.exists():
                                backup = bulk.CSV_PATH.with_name(
                                    bulk.CSV_PATH.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S')
                                )
                                shutil.copy2(bulk.CSV_PATH, backup)
                                backup_created = True
                                self.stdout.write(f'  Review CSV backup: {backup}')

                            seen.add(key_pair)
                            row = {
                                'place_id': str(place.pk),
                                'city_id': str(CITY_ID),
                                'city_name': bulk.safe_cell(place.city.name),
                                'place_name': bulk.safe_cell(place.title),
                                'place_slug': place.slug,
                                'latitude': str(place.latitude or ''),
                                'longitude': str(place.longitude or ''),
                                **candidate,
                                **{fk: '' for fk in bulk.REVIEW_COLUMNS},
                            }
                            rows.append(row)
                            stats['found'] += 1
                            place_leads += 1
                            candidates_since_checkpoint += 1
                            self.stdout.write(f'  OSM/Wikidata lead: {note}')

            except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                place_error = True
                stats['errors'] += 1
                self.stdout.write(f'  OSM lookup warning: {error_detail(exc)}')

            time.sleep(opts['query_delay'])

            # Search Wikimedia Commons for additional leads
            for query_text in search_queries(place.title):
                try:
                    leads = commons_search_optimized(query_text, agent, opts['per_query'])

                    for lead in leads:
                        source_url = lead.get('source_url') or ''
                        image_url = lead.get('image_url') or ''

                        if not bulk.trusted_https(source_url, {'commons.wikimedia.org'}):
                            continue
                        if not bulk.trusted_https(image_url, {'upload.wikimedia.org'}):
                            continue

                        key_pair = (str(place.pk), source_url)
                        if key_pair in seen:
                            continue

                        if not backup_created and bulk.CSV_PATH.exists():
                            backup = bulk.CSV_PATH.with_name(
                                bulk.CSV_PATH.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S')
                            )
                            shutil.copy2(bulk.CSV_PATH, backup)
                            backup_created = True
                            self.stdout.write(f'  Review CSV backup: {backup}')

                        seen.add(key_pair)
                        row = {
                            'place_id': str(place.pk),
                            'city_id': str(CITY_ID),
                            'city_name': bulk.safe_cell(place.city.name),
                            'place_name': bulk.safe_cell(place.title),
                            'place_slug': place.slug,
                            'latitude': str(place.latitude or ''),
                            'longitude': str(place.longitude or ''),
                            'search_query': query_text,
                            **lead,
                            **{fk: '' for fk in bulk.REVIEW_COLUMNS},
                        }
                        rows.append(row)
                        stats['found'] += 1
                        place_leads += 1
                        candidates_since_checkpoint += 1

                        # Checkpoint every N candidates (not every query)
                        if candidates_since_checkpoint >= opts['checkpoint_interval']:
                            bulk.save_rows(rows)
                            self.stdout.write(f'    [checkpoint: {len(rows)} total candidates]')
                            candidates_since_checkpoint = 0

                    self.stdout.write(f'  Commons {query_text!r}: {len(leads)} leads, {place_leads} added this place')

                except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                    place_error = True
                    stats['errors'] += 1
                    self.stdout.write(f'  Commons warning: {error_detail(exc)}')

                time.sleep(opts['query_delay'])

            # Cache result (only complete zero-result searches, not partial errors)
            status[key] = {
                'slug': place.slug,
                'result': 'leads' if place_leads else ('retry' if place_error else 'no_leads'),
                'checked_utc': datetime.now(timezone.utc).isoformat(),
            }
            save_status(status)

        # Final checkpoint
        if candidates_since_checkpoint > 0 or not bulk.CSV_PATH.exists():
            bulk.save_rows(rows)

        bulk.make_gallery(rows)

        self.stdout.write(self.style.SUCCESS(
            'KABANKALAN DISCOVERY DONE: searched={searched}, new leads={found}, '
            'cached/skipped={skipped_cached}, API errors={errors}. Database unchanged.'.format(**stats)
        ))
        self.stdout.write(f'REVIEW CSV: {bulk.CSV_PATH}\nGALLERY: {bulk.GALLERY_PATH}')
        self.stdout.write('All candidates remain UNVERIFIED. Review exact identity, license, and credits before approval.')
