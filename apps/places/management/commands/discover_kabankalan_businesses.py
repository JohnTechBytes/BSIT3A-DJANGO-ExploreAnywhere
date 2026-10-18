"""ExploreAnywhere Phase 6B: OSM business discovery for Kabankalan City.

Public Overpass is an external *mapping* source, NOT a verified business directory.
Default mode fetches a city-boundary-scoped snapshot only. Explicit --import-snapshot
creates inactive, unverified Place records for staff to review before publication.

Source: © OpenStreetMap contributors, ODbL https://www.openstreetmap.org/copyright
"""
from __future__ import annotations

import json
import math
import re
import time
import unicodedata
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.cities.models import City
from apps.core.models import Category
from apps.places.models import Place

CITY_ID = 2
OSM_ENDPOINT = "https://overpass.kumi.systems/api/interpreter"
OVERPASS_ENDPOINTS = (
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
)
ATTRIBUTION = "© OpenStreetMap contributors (ODbL): https://www.openstreetmap.org/copyright"
IDENTITY_RE = re.compile(r"^(kabankalan|kabankalan city|city of kabankalan)$", re.I)
SLUG_RE = re.compile(r"^osm-(node|way|relation)-(\d+)$")
TAGS = {
    "billiards": ("Billiards / Pool Halls", "billiards-pool-halls"),
    "coffee": ("Coffee Shops / Cafes", "coffee-shops-cafes"),
    "barber": ("Barber / Hair Salon", "barber-hair-salon"),
    "restaurant": ("Restaurants / Eateries", "restaurants-eateries"),
    "mall": ("Malls / Shopping Centers", "malls-shopping-centers"),
    "other": ("Other Local Businesses", "other-local-businesses"),
}
MAX_CANDIDATES = 6000


def normalized(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    value = value.encode("ascii", "ignore").decode("ascii")
    return " ".join(re.findall(r"[a-z0-9]+", value.casefold()))


def category_key(tags, title):
    shop = (tags.get("shop") or "").strip().casefold()
    amenity = (tags.get("amenity") or "").strip().casefold()
    sport = (tags.get("sport") or "").strip().casefold()
    leisure = (tags.get("leisure") or "").strip().casefold()
    name = normalized(title)
    if ("billiard" in sport or sport == "pool" and "billiard" in name or
            any(v in name for v in ("billiard", "bilyar", "pool hall"))):
        return "billiards"
    if amenity in {"cafe", "coffee_shop"} or shop in {"coffee", "coffee_shop"}:
        return "coffee"
    if shop in {"hairdresser", "barber"}:
        return "barber"
    if amenity in {"restaurant", "fast_food", "food_court"}:
        return "restaurant"
    if shop in {"mall", "department_store"}:
        return "mall"
    if leisure == "sports_centre" and "pool" in sport:
        return "billiards" if "billiard" in name else "other"
    return "other"


def validated_http_url(value):
    value = str(value or "").strip()
    if len(value) > 200:
        return ""
    p = urlparse(value)
    return value if p.scheme in ("https", "http") and p.netloc else ""


def address_label(tags):
    full = str(tags.get("addr:full") or "").strip()
    if full:
        return full[:255]
    parts = [
        str(tags.get("addr:housenumber") or "").strip(),
        str(tags.get("addr:street") or "").strip(),
        str(tags.get("addr:barangay") or tags.get("addr:suburb") or "").strip(),
        str(tags.get("addr:city") or "").strip(),
    ]
    text = ", ".join(p for p in parts if p)
    return text[:255] if text else "Address not independently verified"


def osm_request(query, *, stage="Overpass request"):
    """Make one HTTPS request; report which stage failed without automatic retries."""
    req = Request(OSM_ENDPOINT, data=urlencode({"data": query}).encode(), headers={
        "User-Agent": "ExploreAnywhere-Kabankalan-School-Project/1.0 (noncommercial OSM review)",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=115) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise CommandError(
            f"{stage} failed: HTTP {exc.code} from Overpass. "
            "The public server may be overloaded or this query may be too expensive. "
            "No database changes; do not repeatedly retry the service."
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise CommandError(
            f"{stage} failed: {exc}. The HTTPS connection or Overpass response "
            "could not be completed. No database changes."
        ) from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("elements"), list):
        raise CommandError(f"{stage} failed: unexpected Overpass response (no elements array).")
    if payload.get("remark") and not payload["elements"]:
        raise CommandError(f"{stage} failed: {str(payload['remark'])[:250]}")
    return payload["elements"]


def discover_boundary_nominatim():
    """Find an OSM *administrative relation* via one Nominatim geocoder request.

    Nominatim is used only to locate an OSM relation ID, never to bulk-search POIs.
    The results must match both the city and province before they can be used.
    """
    query = urlencode({
        "q": "Kabankalan, Negros Occidental, Philippines",
        "format": "jsonv2",
        "addressdetails": "1",
        "limit": "8",
    })
    url = "https://nominatim.openstreetmap.org/search?" + query
    req = Request(url, headers={
        "User-Agent": "ExploreAnywhere-Kabankalan-Educational-Importer/1.0 (OSM relation lookup; one request)",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=30) as response:
            data = json.load(response)
    except HTTPError as exc:
        raise CommandError(
            f"Nominatim boundary lookup failed with HTTP {exc.code}. "
            "No database changes. Do not repeatedly query the public service."
        ) from exc
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        raise CommandError(
            f"Nominatim boundary lookup failed: {exc}. No database changes. "
            "Try a different network later or provide a manually verified --relation-id."
        ) from exc
    if not isinstance(data, list):
        raise CommandError("Nominatim returned an unexpected response; nothing imported.")
    matches = {}
    for item in data:
        if not isinstance(item, dict) or item.get("osm_type") != "relation":
            continue
        try:
            osm_id = int(item.get("osm_id"))
        except (ValueError, TypeError):
            continue
        if osm_id < 1:
            continue
        # Require an exact Kabankalan administrative boundary in Negros Occidental,
        # Philippines. A similarly named place or POI is not acceptable.
        name = str(item.get("name") or "").strip()
        display_name = str(item.get("display_name") or "")
        addr = item.get("address") or {}
        if not isinstance(addr, dict):
            addr = {}
        if not IDENTITY_RE.fullmatch(name):
            # Nominatim may name the place as 'Kabankalan City'; otherwise fail safe.
            continue
        kind = str(item.get("type") or "").casefold()
        klass = str(item.get("class") or item.get("category") or "").casefold()
        if kind != "administrative" or klass != "boundary":
            continue
        geographic_context = normalized(display_name + " " + str(addr.get("province") or "") + " " + str(addr.get("country") or ""))
        if "negros occidental" not in geographic_context or "philippines" not in geographic_context:
            continue
        matches[osm_id] = (osm_id, name, "Nominatim administrative relation")
    if len(matches) == 1:
        return next(iter(matches.values()))
    if not matches:
        raise CommandError(
            "Nominatim did not identify an unambiguous Kabankalan administrative "
            "relation in Negros Occidental. No data changed. Obtain and verify "
            "the OSM relation ID manually; then use --relation-id <ID> --boundary-only."
        )
    raise CommandError(
        "Nominatim returned multiple matching Kabankalan relations: "
        + ", ".join(str(i) for i in matches)
        + ". Choose the correct relation ID manually; no data changed."
    )


def discover_boundary(city, relation_id=None):
    if relation_id is not None:
        if relation_id < 1:
            raise CommandError("--relation-id must be a positive OSM relation ID")
        candidates = osm_request(
            f"[out:json][timeout:25];relation({relation_id});out tags;",
            stage="Kabankalan boundary lookup by OSM relation ID",
        )
    else:
        # Exact-name tag indexes are substantially cheaper than the previous
        # unbounded global regex scan for relation names. This only discovers
        # candidates; the exact boundary tags are still validated below.
        query = ("[out:json][timeout:25];("
                 'rel["boundary"="administrative"]["name"="Kabankalan"];'
                 'rel["boundary"="administrative"]["name"="Kabankalan City"];'
                 'rel["boundary"="administrative"]["name"="City of Kabankalan"];'
                 ");out tags;")
        candidates = osm_request(query, stage="Exact-name Kabankalan boundary lookup")
    matching = []
    for item in candidates:
        if item.get("type") != "relation":
            continue
        tags = item.get("tags") or {}
        name = tags.get("name") or ""
        if tags.get("boundary") != "administrative" or not IDENTITY_RE.fullmatch(name.strip()):
            continue
        candidate_id = item.get("id")
        if isinstance(candidate_id, int) and candidate_id > 0:
            matching.append((candidate_id, name, str(tags.get("admin_level") or "unknown")))
    if not matching:
        raise CommandError(
            "No exact Kabankalan City administrative boundary was found in this "
            "lightweight OSM query. Nothing was imported. Inspect the OSM boundary "
            "manually and use --relation-id <VERIFIED_ID> if available; "
            "do not use an unverified radius."
        )
    if len(matching) != 1:
        lines = ", ".join(f"{rid} ({name}, level {level})" for rid, name, level in matching)
        raise CommandError(
            f"Ambiguous Kabankalan administrative boundaries: {lines}. "
            "Choose the correct boundary manually with --relation-id; refusing to guess."
        )
    return matching[0]


def resolve_boundary_geometry(relation_id):
    """Retrieve one verified city polygon for post-filtering bbox results.

    Nominatim is used only for one OSM relation geometry lookup, never POI search.
    A city bounding box alone is NOT proof that a business lies within the city.
    """
    query = urlencode({
        "osm_ids": f"R{relation_id}",
        "format": "jsonv2",
        "polygon_geojson": "1",
        "addressdetails": "1",
    })
    req = Request("https://nominatim.openstreetmap.org/lookup?" + query, headers={
        "User-Agent": "ExploreAnywhere-Kabankalan-Educational-Importer/1.0 (one city polygon lookup)",
        "Accept": "application/json",
    })
    try:
        with urlopen(req, timeout=40) as response:
            raw = response.read(10_000_001)
        if len(raw) > 10_000_000:
            raise CommandError("Nominatim city polygon exceeds safety limit; no query executed")
        data = json.loads(raw)
    except HTTPError as exc:
        raise CommandError(f"Nominatim polygon lookup HTTP {exc.code}; no Overpass query attempted") from exc
    except (URLError, TimeoutError, OSError, ValueError) as exc:
        raise CommandError(f"Nominatim polygon lookup failed: {exc}; no Overpass query attempted") from exc
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        raise CommandError("Ambiguous or missing Kabankalan relation geometry; refusing bbox discovery")
    item = data[0]
    if item.get("osm_type") != "relation" or str(item.get("osm_id")) != str(relation_id):
        raise CommandError("Nominatim returned a different OSM relation; refusing bbox discovery")
    name = str(item.get("name") or "").strip()
    location_text = normalized(str(item.get("display_name") or ""))
    if not IDENTITY_RE.fullmatch(name) or "negros occidental" not in location_text or "philippines" not in location_text:
        raise CommandError("Nominatim geometry is not clearly Kabankalan City, Negros Occidental")
    if str(item.get("type") or "").casefold() != "administrative" or str(item.get("category") or item.get("class") or "").casefold() != "boundary":
        raise CommandError("Nominatim relation is not an administrative boundary")
    geom = item.get("geojson")
    if not isinstance(geom, dict) or geom.get("type") not in ("Polygon", "MultiPolygon"):
        raise CommandError("Kabankalan relation has no usable polygon geometry")
    try:
        s, n, w, e = [float(v) for v in item["boundingbox"]]
    except (KeyError, TypeError, ValueError) as exc:
        raise CommandError("Nominatim boundary has no valid bounding box") from exc
    if not (math.isfinite(s) and math.isfinite(n) and math.isfinite(w) and math.isfinite(e)
            and 0 < n - s < 1.5 and 0 < e - w < 1.5
            and -90 <= s < n <= 90 and -180 <= w < e <= 180):
        raise CommandError("Unexpected Kabankalan bounding box size or coordinates")
    return (s, w, n, e), geom


def _on_edge(x, y, ax, ay, bx, by):
    cross = (x - ax) * (by - ay) - (y - ay) * (bx - ax)
    return abs(cross) <= 1e-9 and min(ax, bx) - 1e-9 <= x <= max(ax, bx) + 1e-9 and min(ay, by) - 1e-9 <= y <= max(ay, by) + 1e-9


def _in_ring(lon, lat, ring):
    if not isinstance(ring, list) or len(ring) < 4:
        return False
    inside = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        try:
            ax, ay, bx, by = float(a[0]), float(a[1]), float(b[0]), float(b[1])
        except (TypeError, ValueError, IndexError):
            return False
        if _on_edge(lon, lat, ax, ay, bx, by):
            return True
        if ((ay > lat) != (by > lat)) and lon < (bx - ax) * (lat - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def _in_polygon(lon, lat, rings):
    if not rings or not _in_ring(lon, lat, rings[0]):
        return False
    return not any(_in_ring(lon, lat, hole) for hole in rings[1:])


def within_boundary(latitude, longitude, geometry):
    """Conservative local post-filter using the verified OSM city polygon."""
    try:
        lat, lon = float(latitude), float(longitude)
        if not (math.isfinite(lat) and math.isfinite(lon)):
            return False
        coords = geometry["coordinates"]
        if geometry["type"] == "Polygon":
            return _in_polygon(lon, lat, coords)
        if geometry["type"] == "MultiPolygon":
            return any(_in_polygon(lon, lat, rings) for rings in coords)
    except (KeyError, TypeError, ValueError, IndexError, OverflowError, RecursionError):
        return False
    return False


def probe_coffee_bbox(bbox):
    """One tiny, read-only query. Tests bbox syntax and server acceptance."""
    south, west, north, east = bbox
    mid_lat, mid_lon = (south + north) / 2, (west + east) / 2
    # A small window entirely inside the city's bounding rectangle.
    dy, dx = min(0.01, (north - south) / 8), min(0.01, (east - west) / 8)
    tiny = f"{mid_lat-dy:.6f},{mid_lon-dx:.6f},{mid_lat+dy:.6f},{mid_lon+dx:.6f}"
    query = f'[out:json][timeout:15];node["amenity"="cafe"]({tiny});out 5;'
    return osm_request(query, stage="Tiny coffee bbox probe")


def fetch_points(relation_id, only_category=None, bbox=None):
    """Retrieve one named category at a time inside the verified OSM city area.

    Smaller requests reduce public Overpass server load. If any request fails,
    no incomplete or misleading 'all businesses' snapshot will be written.
    """
    requests = {
        "billiards": (
            'nwr(area.kab)["sport"~"billiards|pool",i];',
            'nwr(area.kab)["name"~"billiard|bilyar|pool hall",i];',
        ),
        "coffee": (
            'nwr(area.kab)["amenity"~"^(cafe|coffee_shop)$"];',
            'nwr(area.kab)["shop"~"^(coffee|coffee_shop)$"];',
        ),
        "barber": ('nwr(area.kab)["shop"~"^(hairdresser|barber)$"];',),
        "restaurant": ('nwr(area.kab)["amenity"~"^(restaurant|fast_food|food_court)$"];',),
        "mall": ('nwr(area.kab)["shop"~"^(mall|department_store)$"];',),
        "other": (
            'nwr(area.kab)["shop"];',
            'nwr(area.kab)["amenity"~"^(bar|pub|bank|pharmacy|clinic|dentist|doctors|hospital|fuel|car_wash|marketplace)$"];',
            'nwr(area.kab)["leisure"~"^(sports_centre|bowling_alley|fitness_centre)$"];',
        ),
    }
    keys = [only_category] if only_category else list(requests)
    combined = {}
    for index, key in enumerate(keys):
        if index:
            time.sleep(3)  # be considerate to a shared public Overpass service
        filters = "\n  ".join(requests[key])
        if bbox is None:
            query = (f'[out:json][timeout:75];\n'
                     f'relation({relation_id});map_to_area->.kab;\n'
                     f'(\n  {filters}\n);\nout center tags;')
        else:
            south, west, north, east = bbox
            window = f"({south:.6f},{west:.6f},{north:.6f},{east:.6f})"
            bounded_filters = filters.replace("(area.kab)", window)
            query = (f'[out:json][timeout:60];\n'
                     f'(\n  {bounded_filters}\n);\nout center tags;')
        elements = osm_request(query, stage=f"Kabankalan {key} business query")
        for item in elements:
            if item.get("type") in ("node", "way", "relation") and isinstance(item.get("id"), int):
                combined[(item["type"], item["id"])] = item
    if not combined:
        raise CommandError(
            "No mapped businesses were returned for the chosen category/categories. "
            "No empty snapshot created. OSM coverage may be incomplete."
        )
    return list(combined.values())


def extract_candidates(elements):
    candidates = {}
    for item in elements:
        try:
            tp, oid = item.get("type"), int(item.get("id"))
            if tp not in {"node", "way", "relation"} or oid < 1:
                continue
            tags = item.get("tags") or {}
            name = str(tags.get("name") or "").strip()
            if not name or len(name) > 255:
                continue
            center = item.get("center") or item
            lat = Decimal(str(center.get("lat")))
            lon = Decimal(str(center.get("lon")))
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue
        except (ValueError, TypeError, InvalidOperation, AttributeError):
            continue
        key = f"osm-{tp}-{oid}"
        website = validated_http_url(tags.get("website") or tags.get("contact:website"))
        category = category_key(tags, name)
        raw_phone = str(tags.get("phone") or tags.get("contact:phone") or "")
        candidates[key] = {
            "slug": key,
            "name": name,
            "category": category,
            "address": address_label(tags),
            "barangay": str(tags.get("addr:barangay") or "").strip()[:100],
            "lat": str(lat.quantize(Decimal("0.000001"))),
            "lon": str(lon.quantize(Decimal("0.000001"))),
            "phone": raw_phone[:50],
            "website": website,
            "osm_url": f"https://www.openstreetmap.org/{tp}/{oid}",
        }
        if len(candidates) > MAX_CANDIDATES:
            raise CommandError(f"Too many points (> {MAX_CANDIDATES}). Refusing an unexpected response.")
    return sorted(candidates.values(), key=lambda p: (p["category"], normalized(p["name"]), p["slug"]))


def distance_meters(a, b, x, y):
    """Rough great-circle distance, used only to flag potential duplicates."""
    r = 6371000
    phi1, phi2 = math.radians(float(a)), math.radians(float(x))
    delta_lat = phi2 - phi1
    delta_lon = math.radians(float(y) - float(b))
    h = math.sin(delta_lat / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lon / 2)**2
    return 2 * r * math.asin(min(1, math.sqrt(h)))


def validate_snapshot(raw):
    if not isinstance(raw, dict) or raw.get("format") != "exploreanywhere-osm-kabankalan-v1":
        raise CommandError("This is not a Phase 6B Kabankalan snapshot.")
    if raw.get("city_id") != CITY_ID or raw.get("city_name") != "Kabankalan":
        raise CommandError("Snapshot is for the wrong city. Refusing import.")
    if not isinstance(raw.get("relation_id"), int) or raw["relation_id"] <= 0:
        raise CommandError("Snapshot has no valid OSM boundary reference.")
    places = raw.get("places")
    if not isinstance(places, list) or len(places) > MAX_CANDIDATES:
        raise CommandError("Invalid snapshot candidate list size.")
    result = []
    seen = set()
    for value in places:
        if not isinstance(value, dict) or not SLUG_RE.fullmatch(str(value.get("slug", ""))):
            raise CommandError("Snapshot contains a malformed OSM ID.")
        slug = value["slug"]
        if slug in seen:
            raise CommandError("Snapshot contains repeated OSM IDs.")
        seen.add(slug)
        if value.get("category") not in TAGS:
            raise CommandError(f"Unexpected category for {slug}.")
        name = value.get("name", "")
        if not isinstance(name, str) or not (0 < len(name.strip()) <= 255):
            raise CommandError(f"Invalid business name for {slug}.")
        try:
            la, lo = Decimal(str(value["lat"])), Decimal(str(value["lon"]))
            if not (Decimal(-90) <= la <= Decimal(90) and Decimal(-180) <= lo <= Decimal(180)):
                raise ValueError()
        except (ValueError, InvalidOperation, KeyError) as exc:
            raise CommandError(f"Invalid GPS coordinates for {slug}.") from exc
        result.append(value)
    return result


class Command(BaseCommand):
    help = (
        "Discover named OSM Kabankalan businesses (preview only), or explicitly "
        "import reviewed candidates as unpublished/unverified Place records."
    )

    def add_arguments(self, parser):
        parser.add_argument("--overpass-endpoint", choices=OVERPASS_ENDPOINTS,
                            default=OSM_ENDPOINT,
                            help="HTTPS Overpass interpreter to use (default: overpass.kumi.systems)")
        parser.add_argument("--relation-id", type=int, default=None,
                            help="OSM administrative boundary relation ID if discovery is ambiguous")
        parser.add_argument("--boundary-only", action="store_true",
                            help="Check the Kabankalan OSM boundary without fetching businesses or writing a snapshot")
        parser.add_argument("--boundary-source", choices=("nominatim", "overpass"), default="nominatim",
                            help="Resolve the boundary via Nominatim (default, one lookup) or Overpass")
        parser.add_argument("--category", choices=tuple(TAGS), default=None,
                            help="Fetch only one business category as a smaller preview query")
        parser.add_argument("--query-mode", choices=("area", "bbox"), default="area",
                            help="area=existing Overpass area; bbox=Nominatim polygon-checked fallback")
        parser.add_argument("--probe-bbox", action="store_true",
                            help="Tiny read-only coffee query before attempting a full city bbox fetch")
        parser.add_argument("--snapshot", type=str, default="",
                            help="Write new preview JSON here (default: phase6_imports/OSM_...json)")
        parser.add_argument("--import-snapshot", type=str, default="",
                            help="Create inactive, unverified candidates from a saved JSON snapshot")
        parser.add_argument("--dry-run", action="store_true",
                            help="With --import-snapshot, only show expected creations; never write DB")
        parser.add_argument("--max-new", type=int, default=1500,
                            help="Safety limit for new imported rows per run (default 1500)")

    def handle(self, *args, **options):
        global OSM_ENDPOINT
        OSM_ENDPOINT = options["overpass_endpoint"]
        city = City.objects.filter(
            pk=CITY_ID, name__iexact="Kabankalan", province__iexact="Negros Occidental"
        ).first()
        if city is None:
            raise CommandError("Kabankalan City (city_id=2) was not found. No data changed.")
        max_new = options["max_new"]
        if not 1 <= max_new <= MAX_CANDIDATES:
            raise CommandError("--max-new must be between 1 and 6000")
        if options["import_snapshot"]:
            if options["boundary_only"] or options["probe_bbox"]:
                raise CommandError("--import-snapshot cannot be combined with a fetch probe")
            self.import_snapshot(city, Path(options["import_snapshot"]), options["dry_run"], max_new)
            return
        if options["dry_run"]:
            raise CommandError("--dry-run is only for --import-snapshot; regular fetch is already read-only")
        if options["relation_id"] is not None:
            relation_id, name, admin_level = discover_boundary(city, options["relation_id"])
        elif options["boundary_source"] == "nominatim":
            relation_id, name, admin_level = discover_boundary_nominatim()
        else:
            relation_id, name, admin_level = discover_boundary(city)
        self.stdout.write(f"Kabankalan OSM administrative boundary: {relation_id}, {name}, source {admin_level}")
        if options["boundary_only"]:
            self.stdout.write(self.style.SUCCESS("BOUNDARY ONLY: no business fetch, no snapshot, no database changes."))
            return
        if options["probe_bbox"] and options["query_mode"] != "bbox":
            raise CommandError("--probe-bbox requires --query-mode bbox")
        if options["query_mode"] == "bbox":
            # Respect Nominatim's low-volume usage policy between city lookup and polygon lookup.
            time.sleep(1.2)
            bbox, geometry = resolve_boundary_geometry(relation_id)
            self.stdout.write(f"Verified Kabankalan polygon; bounded window: {bbox}")
            if options["probe_bbox"]:
                time.sleep(2)  # polite gap after Nominatim
                elements = probe_coffee_bbox(bbox)
                self.stdout.write(self.style.SUCCESS(
                    f"BBOX PROBE PASS: Server processed small request; {len(elements)} raw items. "
                    "No snapshot or database changes. Zero items is also a valid result."
                ))
                return
            if not options["category"]:
                raise CommandError("BBox discovery requires --category to limit load on shared OSM infrastructure")
            time.sleep(2)
            candidates = extract_candidates(fetch_points(relation_id, options["category"], bbox=bbox))
            values = [p for p in candidates if within_boundary(p["lat"], p["lon"], geometry)]
            self.stdout.write(f"Polygon-checked candidates: {len(values)} inside Kabankalan of {len(candidates)} bbox candidates")
        else:
            # Existing area-query behavior preserved unchanged for rollback compatibility.
            time.sleep(2)
            values = extract_candidates(fetch_points(relation_id, options["category"]))
        if options["category"] is not None:
            values = [value for value in values if value["category"] == options["category"]]
        if not values:
            raise CommandError("No named OSM business listings available; refusing empty snapshot")
        output = Path(options["snapshot"]) if options["snapshot"] else (
            Path.cwd() / "phase6_imports" / f"kabankalan_osm_{datetime.now(timezone.utc):%Y%m%d_%H%M%S}.json"
        )
        output = output.expanduser().resolve()
        if output.exists():
            raise CommandError(f"Snapshot file already exists: {output}. Won't overwrite it")
        output.parent.mkdir(parents=True, exist_ok=True)
        doc = {
            "format": "exploreanywhere-osm-kabankalan-v1",
            "city_id": CITY_ID,
            "city_name": "Kabankalan",
            "relation_id": relation_id,
            "source": "OpenStreetMap Overpass; not independently verified",
            "attribution": ATTRIBUTION,
            "discovery_category": options["category"] or "all",
            "fetched_utc": datetime.now(timezone.utc).isoformat(),
            "places": values,
        }
        output.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
        counts = {key: sum(p["category"] == key for p in values) for key in TAGS}
        self.stdout.write(self.style.SUCCESS(
            f"PREVIEW: {len(values)} mapped named businesses; categories={counts}"
        ))
        self.stdout.write(f"Saved: {output}")
        self.stdout.write(ATTRIBUTION)
        self.stdout.write(
            "NOT VERIFIED OR COMPLETE: OSM listing ≠ operating business. "
            "Review the JSON first; --import-snapshot creates UNPUBLISHED candidates only."
        )

    def import_snapshot(self, city, filename, dry_run, max_new):
        if not filename.is_file():
            raise CommandError(f"Snapshot not found: {filename}")
        if filename.stat().st_size > 8 * 1024 * 1024:
            raise CommandError("Snapshot too large (>8MB)")
        try:
            raw = json.loads(filename.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError, OSError) as exc:
            raise CommandError("Snapshot is not valid readable JSON") from exc
        candidates = validate_snapshot(raw)
        # Work only with city_id=2, never modify any existing published place.
        existing = list(Place.objects.filter(city=city).values(
            "slug", "title", "latitude", "longitude"
        ))
        by_slug = {p["slug"] for p in existing}
        existing_named = {}
        for p in existing:
            existing_named.setdefault(normalized(p["title"]), []).append(p)
        to_create, existing_slug, possible_duplicates = [], 0, []
        for value in candidates:
            if value["slug"] in by_slug:
                existing_slug += 1
                continue
            same_names = existing_named.get(normalized(value["name"]), ())
            duplicate = False
            for older in same_names:
                if older["latitude"] is None or older["longitude"] is None:
                    duplicate = True  # be conservative when existing location is unknown
                elif distance_meters(older["latitude"], older["longitude"], value["lat"], value["lon"]) < 300:
                    duplicate = True
                if duplicate:
                    break
            if duplicate:
                possible_duplicates.append(value)
                continue
            to_create.append(value)
        if len(to_create) > max_new:
            raise CommandError(
                f"{len(to_create)} new candidates exceed --max-new={max_new}. "
                "Inspect the JSON and explicitly raise the limit if correct."
            )
        self.stdout.write(
            f"SNAPSHOT: {len(candidates)} records | new: {len(to_create)} | "
            f"existing OSM IDs: {existing_slug} | possible duplicates skipped: {len(possible_duplicates)}"
        )
        for value in to_create[:12]:
            self.stdout.write(f"  NEW [{value['category']}] {value['name']} — {value['osm_url']}")
        if possible_duplicates:
            self.stdout.write("POSSIBLE DUPLICATES (skipped; do not delete the originals):")
            for value in possible_duplicates[:10]:
                self.stdout.write(f"  {value['name']} — {value['osm_url']}")
        if dry_run:
            self.stdout.write("DRY RUN: no database records changed.")
            return
        if not to_create:
            self.stdout.write("No new records to stage. Existing records unchanged.")
            return
        created = 0
        with transaction.atomic():
            cats = {}
            for key in sorted({v["category"] for v in to_create}):
                title, slug = TAGS[key]
                found = Category.objects.filter(slug=slug).first()
                if found is None:
                    found = Category.objects.filter(name__iexact=title).first()
                if found is None:
                    found = Category.objects.create(name=title, slug=slug)
                cats[key] = found
            for value in to_create:
                place, is_new = Place.objects.get_or_create(
                    city=city, slug=value["slug"], defaults={
                        "title": value["name"],
                        "category": cats[value["category"]],
                        "address": str(value["address"])[:255],
                        "barangay": str(value.get("barangay") or "")[:100],
                        "latitude": Decimal(value["lat"]),
                        "longitude": Decimal(value["lon"]),
                        "phone": str(value.get("phone") or "")[:50],
                        "website": validated_http_url(value.get("website")),
                        "description": "",  # never generate claims or fabricate descriptions
                        "is_active": False,
                        "is_verified": False,
                    },
                )
                created += int(is_new)
        self.stdout.write(self.style.SUCCESS(
            f"STAGED: {created} NEW INACTIVE + UNVERIFIED Kabankalan places. "
            "Existing destinations were NOT modified."
        ))
        self.stdout.write(
            "Admin: /admin/places/place/ — filter unpublished, verify address/identity, "
            "coordinates, operations, license-compliant photos, and hobby/category; "
            "publish only accurate and adequately checked records."
        )
        self.stdout.write(ATTRIBUTION)
