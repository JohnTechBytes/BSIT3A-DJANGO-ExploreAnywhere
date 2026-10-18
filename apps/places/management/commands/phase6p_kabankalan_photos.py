"""ExploreAnywhere Phase 6P.3 — Kabankalan-only reviewed-photo discovery.

Install alongside phase6p_bulk_photos.py in apps/places/management/commands/.

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
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlsplit

from django.core.management.base import CommandError

from apps.cities.models import City
from apps.places.models import Place
from apps.places.management.commands import phase6p_bulk_photos as bulk
from apps.places.management.commands.phase6o_business_photos import (
    commons_filename, commons_metadata, error_detail, osm_tags,
)
from apps.places.management.commands.phase6o_search_commons import commons_search

CITY_ID = 2
STATUS_FILE = bulk.REPORT_DIR / 'kabankalan_photo_discovery_status.json'


def search_queries(name):
    """Location-qualified discovery ONLY; never automatic identity verification."""
    clean = re.sub(r'\s+', ' ', str(name or '')).replace('"', '').strip()[:90]
    if not clean:
        return ()
    variants = [clean]
    variant = clean.replace('’', "'").replace('–', '-').replace('-', ' ')
    if variant != clean:
        variants.append(variant)
    if '&' in clean:
        variants.append(clean.replace('&', 'and'))
    results = []
    for title in variants[:2]:
        results.extend((f'"{title}" Kabankalan', f'"{title}" "Negros Occidental"'))
    # Wikimedia search ranking differs between quoted and unquoted phrases.
    results.extend((f'{clean} Kabankalan',))
    return tuple(dict.fromkeys(results[:5]))


def load_status():
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
        'match_status': 'EXACT OSM REFERENCE — photo identity and rights still require review',
        **info,
    }, method


class Command(bulk.Command):
    help = ('Phase 6P.3 Kabankalan-only photo discovery and review; '
            'no MySQL writes while discovering')

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('--published-first', action='store_true',
                            help='Prioritize verified active places when paging through Kabankalan')

    def handle(self, *args, **opts):
        if opts.get('city_id') not in (None, CITY_ID):
            raise CommandError('This command is Kabankalan-only. Use --city-id 2.')
        city = City.objects.filter(pk=CITY_ID).first()
        if city is None or city.name.strip().casefold() != 'kabankalan':
            raise CommandError('City 2 is not Kabankalan. No changes made.')
        opts['city_id'] = CITY_ID
        return super().handle(*args, **opts)

    def discover(self, rows, opts):
        agent = os.environ.get('EXPLOREANYWHERE_PHOTO_USER_AGENT', '').strip()
        if not agent or '@' not in agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set EXPLOREANYWHERE_PHOTO_USER_AGENT with your real contact email.')
        # Keep original review CSV and reviewer decisions. Do not reset prior leads.
        status = load_status()
        inventory = list(Place.objects.filter(city_id=CITY_ID).select_related('city').order_by('id'))
        if opts.get('published_first'):
            inventory.sort(key=lambda p: (not (p.is_active and p.is_verified), p.pk))
        window = inventory[opts['offset']:opts['offset'] + opts['limit']]
        targets = [p for p in window if not (p.cover_image or p.cover_image_url)]
        missing = sum(not (p.cover_image or p.cover_image_url) for p in inventory)
        self.stdout.write(f'KABANKALAN ONLY: {len(targets)} missing-cover places in window '
                          f'{opts["offset"]}–{opts["offset"] + opts["limit"] - 1} '
                          f'of {len(inventory)}; {missing} missing covers total. DATABASE READ ONLY.')
        seen = {(r['place_id'], r['source_url']) for r in rows}
        prior_leads = {r['place_id'] for r in rows}
        stats = {'searched': 0, 'found': 0, 'skipped_cached': 0, 'errors': 0}
        backup_created = False

        def add_candidate(place, candidate):
            nonlocal backup_created
            source_url = candidate.get('source_url') or ''
            image_url = candidate.get('image_url') or ''
            if not bulk.trusted_https(source_url, {'commons.wikimedia.org'}):
                return False
            if not bulk.trusted_https(image_url, {'upload.wikimedia.org'}):
                return False
            key = (str(place.pk), source_url)
            if key in seen:
                return False
            if not backup_created and bulk.CSV_PATH.exists():
                backup = bulk.CSV_PATH.with_name(bulk.CSV_PATH.name + '.backup-' +
                                                 datetime.now().strftime('%Y%m%d-%H%M%S'))
                shutil.copy2(bulk.CSV_PATH, backup)
                backup_created = True
                self.stdout.write('  Review CSV backup: ' + str(backup))
            seen.add(key)
            row = {
                'place_id': str(place.pk), 'city_id': str(CITY_ID),
                'city_name': bulk.safe_cell(place.city.name),
                'place_name': bulk.safe_cell(place.title),
                'place_slug': place.slug,
                'latitude': str(place.latitude or ''),
                'longitude': str(place.longitude or ''),
                **candidate,
                **{key: '' for key in bulk.REVIEW_COLUMNS},
            }
            rows.append(row)
            bulk.save_rows(rows)
            stats['found'] += 1
            return True

        for index, place in enumerate(targets, 1):
            key = str(place.pk)
            cached = status.get(key)
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
            try:
                tags = osm_tags(place.slug, agent) if bulk.re.fullmatch(r'osm-(?:node|way|relation)-\d+',place.slug or '') else {}
                candidate, note = linked_candidate(tags, agent)
                if candidate and add_candidate(place, candidate):
                    place_leads += 1
                    self.stdout.write(f'  OSM/Wikidata lead: {note}')
            except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                place_error = True
                stats['errors'] += 1
                self.stdout.write('  OSM lookup warning: ' + error_detail(exc))
            time.sleep(0.8)
            for query in search_queries(place.title):
                try:
                    leads = commons_search(query, agent, opts['per_query'])
                    for lead in leads:
                        if add_candidate(place, {'search_query': query, **lead}):
                            place_leads += 1
                    self.stdout.write(f'  Commons {query!r}: {len(leads)} leads')
                except (HTTPError, URLError, TimeoutError, OSError, ValueError, KeyError) as exc:
                    place_error = True
                    stats['errors'] += 1
                    self.stdout.write('  Commons warning: ' + error_detail(exc))
                time.sleep(0.8)
            # Cache only a COMPLETE zero-result search, never a partial error.
            status[key] = {
                'slug': place.slug,
                'result': 'leads' if place_leads else ('retry' if place_error else 'no_leads'),
                'checked_utc': datetime.now(timezone.utc).isoformat(),
            }
            save_status(status)
        if not bulk.CSV_PATH.exists():
            bulk.save_rows(rows)
        bulk.make_gallery(rows)
        self.stdout.write(self.style.SUCCESS(
            'KABANKALAN DISCOVERY DONE: searched={searched}, new leads={found}, '
            'cached/skipped={skipped_cached}, API errors={errors}. Database unchanged.'.format(**stats)
        ))
        self.stdout.write(f'REVIEW CSV: {bulk.CSV_PATH}\nGALLERY: {bulk.GALLERY_PATH}')
        self.stdout.write('All candidates remain UNVERIFIED. Review exact identity, license, and credits before approval.')
