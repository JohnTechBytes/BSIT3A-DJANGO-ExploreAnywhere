"""ExploreAnywhere Phase 6C: local OSM extract -> review-only Kabankalan snapshot.

No Overpass calls; the one-time polygon lookup uses Nominatim unless cached.
The snapshot must still be reviewed and explicitly staged through the existing
'discover_kabankalan_businesses --import-snapshot' management command.

Data © OpenStreetMap contributors, ODbL; https://www.openstreetmap.org/copyright
"""
from __future__ import annotations

import json
import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from apps.cities.models import City
from apps.places.management.commands.discover_kabankalan_businesses import (
    CITY_ID, ATTRIBUTION, MAX_CANDIDATES, TAGS, category_key,
    normalized, extract_candidates, within_boundary, resolve_boundary_geometry,
)

RELATION = 3740502
BOX = (9.5766892, 122.7175207, 10.1219676, 122.9809772)  # screening only; polygon is authoritative
ALLOWED_AMENITY = {
    'cafe','coffee_shop','restaurant','fast_food','food_court','bar','pub',
    'bank','pharmacy','clinic','dentist','doctors','hospital','fuel','car_wash','marketplace',
}
ALLOWED_LEISURE = {'sports_centre','bowling_alley','fitness_centre'}


def is_business(tags, name):
    if not name:
        return False
    return bool(tags.get('shop') or
                tags.get('amenity', '').lower() in ALLOWED_AMENITY or
                tags.get('leisure', '').lower() in ALLOWED_LEISURE or
                'billiard' in str(tags.get('sport','')).lower())


def valid_coords(lat, lon):
    try:
        la, lo = float(lat), float(lon)
        return math.isfinite(la) and math.isfinite(lo) and BOX[0] <= la <= BOX[2] and BOX[1] <= lo <= BOX[3]
    except (TypeError, ValueError, OverflowError):
        return False


def read_osm_xml(file_path, add):
    """Stream nodes/ways; standard OSM XML places nodes before ways.

    Store only node coordinates in the Kabankalan bounding rectangle; retain no
    XML trees or unrelated metadata. Geometric polygon validation is after parsing.
    """
    nodes = {}
    read = {'node': 0, 'way': 0}
    try:
        for _, element in ET.iterparse(file_path, events=('end',)):
            if element.tag not in ('node','way'):
                continue
            osm_type = element.tag
            read[osm_type] += 1
            osm_id = element.get('id')
            if osm_type == 'node':
                lat, lon = element.get('lat'), element.get('lon')
                if valid_coords(lat, lon):
                    nodes[osm_id] = (float(lat), float(lon))
                else:
                    nodes.pop(osm_id, None)
            else:
                refs = [e.get('ref') for e in element if e.tag == 'nd']
                locs = [nodes[r] for r in refs if r in nodes]
                if not locs:
                    element.clear()
                    continue
                lat = sum(p[0] for p in locs)/len(locs)
                lon = sum(p[1] for p in locs)/len(locs)
            if osm_type == 'node' and not valid_coords(lat,lon):
                element.clear()
                continue
            tags = {e.get('k'): e.get('v','') for e in element if e.tag == 'tag' and e.get('k')}
            if is_business(tags, tags.get('name','')):
                add({'type': osm_type, 'id': int(osm_id),
                     'tags': tags, 'lat': lat, 'lon': lon})
            element.clear()
    except (ET.ParseError, OSError, ValueError) as exc:
        raise CommandError(f'Cannot parse OSM XML: {exc}') from exc
    return read


def read_pbf(file_path, add):
    try:
        import osmium  # pip install osmium inside the virtual environment
    except ImportError as exc:
        raise CommandError('PBF files require the optional osmium package: python -m pip install osmium') from exc
    counts = {'node': 0, 'way': 0}
    class Visitor(osmium.SimpleHandler):
        def node(self, n):
            counts['node'] += 1
            tags = dict(n.tags)
            if not is_business(tags, tags.get('name','')):
                return
            if n.location.valid():
                lat, lon = n.location.lat, n.location.lon
                if valid_coords(lat,lon):
                    add({'type':'node','id':n.id,'tags':tags,'lat':lat,'lon':lon})
        def way(self, w):
            counts['way'] += 1
            tags = dict(w.tags)
            if not is_business(tags, tags.get('name','')):
                return
            locs = [(n.location.lat, n.location.lon) for n in w.nodes if n.location.valid()]
            if not locs:
                return
            lat = sum(la for la,_ in locs)/len(locs)
            lon = sum(lo for _,lo in locs)/len(locs)
            if valid_coords(lat,lon):
                add({'type':'way','id':w.id,'tags':tags,'lat':lat,'lon':lon})
    try:
        Visitor().apply_file(str(file_path), locations=True)
    except Exception as exc:
        raise CommandError(f'Could not read OSM PBF: {exc}') from exc
    return counts


def get_city_polygon(cache_path):
    if cache_path.is_file():
        try:
            obj = json.loads(cache_path.read_text(encoding='utf-8'))
            if (obj['relation_id'] != RELATION or obj['city'] != 'Kabankalan' or
                obj['geometry']['type'] not in ('Polygon', 'MultiPolygon')):
                raise ValueError('city/relation/geometry mismatch')
            geom = obj['geometry']
            if not isinstance(geom.get('coordinates'), list):
                raise ValueError('invalid coordinates')
            return geom, 'cached verified city polygon'
        except (OSError, ValueError, TypeError, KeyError) as exc:
            raise CommandError(f'Polygon cache invalid: {exc}. Remove only that cache file after inspecting it.') from exc
    _, geom = resolve_boundary_geometry(RELATION)  # Nominatim, NOT Overpass; verified place context
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps({'relation_id':RELATION,'city':'Kabankalan',
                                     'source':'Nominatim administrative relation geometry',
                                     'geometry':geom},ensure_ascii=False), encoding='utf-8')
    return geom, 'Nominatim (cached for reuse)'


class Command(BaseCommand):
    help = 'Read an offline OSM extract (.osm or .osm.pbf) and create a review-only Kabankalan business snapshot.'

    def add_arguments(self, parser):
        parser.add_argument('osm_file', help='Local OSM .osm or .osm.pbf export; no Overpass API access')
        parser.add_argument('--category', choices=tuple(TAGS), default=None,
                            help='Optional category to include; default all supported business categories')
        parser.add_argument('--snapshot', default='', help='New output JSON file, never overwrites')
        parser.add_argument('--polygon-cache', default='phase6_imports/kabankalan_polygon_3740502.json')

    def handle(self, *args, **options):
        path = Path(options['osm_file']).expanduser().resolve()
        if not path.is_file() or not path.name.lower().endswith(('.osm','.osm.pbf')):
            raise CommandError('Provide a readable .osm or .osm.pbf file; no database changes.')
        if path.stat().st_size > 1_200_000_000:
            raise CommandError('Extract exceeds 1.2 GB; request a smaller city extract. No database changes.')
        if not City.objects.filter(pk=CITY_ID,name__iexact='Kabankalan',province__iexact='Negros Occidental').exists():
            raise CommandError('Expected Kabankalan city_id=2 is missing; no changes.')
        cache = Path(options['polygon_cache']).expanduser().resolve()
        geometry, origin = get_city_polygon(cache)
        self.stdout.write(f'Kabankalan polygon: OSM relation {RELATION}; {origin}')
        elements = []
        scanned = 0
        def add(element):
            nonlocal scanned
            scanned += 1
            if within_boundary(element['lat'],element['lon'],geometry):
                elements.append(element)
                if len(elements) > MAX_CANDIDATES:
                    raise CommandError(f'Too many candidates (> {MAX_CANDIDATES}). Use a smaller OSM extract.')
        if path.name.lower().endswith('.osm.pbf'):
            counts = read_pbf(path, add)
        else:
            counts = read_osm_xml(path, add)
        candidates = extract_candidates(elements)
        if options['category']:
            candidates = [x for x in candidates if x['category'] == options['category']]
        self.stdout.write(f'OSM features scanned: {counts}; business features screened: {scanned}; '
                          f'inside Kabankalan: {len(elements)}; category results: {len(candidates)}')
        if not candidates:
            self.stdout.write(self.style.WARNING('No matching named businesses found in this extract. No snapshot created.'))
            return
        output = (Path(options['snapshot']).expanduser().resolve() if options['snapshot'] else
                  (Path.cwd() / 'phase6_imports' / f'kabankalan_osm_offline_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json'))
        if output.exists():
            raise CommandError(f'Output already exists; refusing overwrite: {output}')
        output.parent.mkdir(parents=True, exist_ok=True)
        doc = {'format':'exploreanywhere-osm-kabankalan-v1',
               'city_id':CITY_ID,'city_name':'Kabankalan','relation_id':RELATION,
               'source':'OpenStreetMap offline extract; not independently verified',
               'attribution':ATTRIBUTION,'discovery_category':options['category'] or 'all',
               'fetched_utc':datetime.now(timezone.utc).isoformat(),'places':candidates}
        serialized = json.dumps(doc,ensure_ascii=False,indent=2)
        if len(serialized.encode('utf-8')) > 8*1024*1024:
            raise CommandError('Snapshot exceeds 8 MB import safety limit; use a single --category')
        output.write_text(serialized,encoding='utf-8')
        groups = {c:sum(p['category']==c for p in candidates) for c in TAGS}
        self.stdout.write(self.style.SUCCESS(f'PREVIEW CREATED: {len(candidates)} candidate(s) by category: {groups}'))
        self.stdout.write(f'Saved to: {output}')
        self.stdout.write('NO DATABASE CHANGES. Imported candidates still require Admin verification and publication.')
        self.stdout.write(ATTRIBUTION)
