
import json
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import certifi

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.cities.models import City
from apps.places.models import Place


OVERPASS_ENDPOINTS = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
    "https://overpass-api.de/api/interpreter",
]

QUERY_FILTERS = [
    '["tourism"~"^(attraction|museum|gallery|viewpoint|zoo|theme_park|aquarium|artwork)$"]',
    '["historic"~"^(castle|monument|memorial|archaeological_site|ruins|fort)$"]',
    '["natural"~"^(beach|waterfall|cave_entrance)$"]',
    '["leisure"~"^(park|nature_reserve|garden)$"]',
]


class Command(BaseCommand):
    help = "Fetch, cache and import OSM attractions."

    def add_arguments(self, parser):
        parser.add_argument("--city-id", type=int)
        parser.add_argument("--limit-cities", type=int, default=1)
        parser.add_argument("--radius", type=int, default=3000)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument(
            "--offline",
            action="store_true",
            help="Use cached data only; never contact Overpass."
        )
        parser.add_argument(
            "--refresh",
            action="store_true",
            help="Request fresh data instead of reusing cache."
        )

    def handle(self, *args, **options):
        radius = options["radius"]
        limit = options["limit_cities"]

        if not 500 <= radius <= 10000:
            raise CommandError(
                "Radius must be between 500 and 10000 metres."
            )

        if not 1 <= limit <= 10:
            raise CommandError(
                "Limit must be between 1 and 10."
            )

        if options["offline"] and options["refresh"]:
            raise CommandError(
                "--offline and --refresh cannot be combined."
            )

        cities = City.objects.filter(
            latitude__isnull=False,
            longitude__isnull=False
        )

        if options["city_id"] is not None:
            cities = cities.filter(pk=options["city_id"])

        cities = list(cities.order_by("pk")[:limit])

        if not cities:
            raise CommandError(
                "No matching city with coordinates."
            )

        cache_dir = (
            Path(settings.BASE_DIR)
            / "data"
            / "osm_cache"
        )
        cache_dir.mkdir(parents=True, exist_ok=True)

        self.stdout.write(
            "Source: OpenStreetMap contributors (ODbL)."
        )
        self.stdout.write(
            "Warning: Radius searches may include "
            "nearby municipalities."
        )

        for index, city in enumerate(cities):
            if index:
                time.sleep(3)

            cache_file = cache_dir / (
                f"city_{city.pk}_radius_{radius}.json"
            )

            self.stdout.write(
                f"\nCity: {city.name} (ID {city.pk})"
            )

            elements = None

            if cache_file.exists() and not options["refresh"]:
                try:
                    with cache_file.open(
                        "r", encoding="utf-8"
                    ) as file:
                        cached = json.load(file)

                    if (
                        cached.get("city_id") == city.pk
                        and cached.get("radius") == radius
                        and cached.get("latitude")
                            == str(city.latitude)
                        and cached.get("longitude")
                            == str(city.longitude)
                        and isinstance(
                            cached.get("elements"), list
                        )
                    ):
                        elements = cached["elements"]
                        self.stdout.write(
                            "Loaded saved JSON cache."
                        )
                    else:
                        self.stdout.write(
                            "Cache metadata mismatch."
                        )

                except (OSError, ValueError, TypeError) as error:
                    self.stderr.write(
                        f"Cache error: {error}"
                    )

            if elements is None:
                if options["offline"]:
                    self.stderr.write(
                        "No valid local cache for this city "
                        "and radius."
                    )
                    continue

                try:
                    elements = self.fetch(
                        float(city.latitude),
                        float(city.longitude),
                        radius
                    )
                except (
                    HTTPError,
                    URLError,
                    TimeoutError,
                    ValueError,
                    OSError,
                ) as error:
                    self.stderr.write(
                        f"Fetch failed: {error}"
                    )
                    continue

                cache_data = {
                    "city_id": city.pk,
                    "city_name": city.name,
                    "latitude": str(city.latitude),
                    "longitude": str(city.longitude),
                    "radius": radius,
                    "source": "OpenStreetMap",
                    "elements": elements,
                }

                with cache_file.open(
                    "w", encoding="utf-8"
                ) as file:
                    json.dump(
                        cache_data,
                        file,
                        ensure_ascii=False,
                        indent=2
                    )

                self.stdout.write(
                    f"Saved cache: {cache_file}"
                )

            candidates = self.parse_elements(elements, city)

            self.stdout.write(
                f"Named attractions found: {len(candidates)}"
            )

            for slug, data in list(
                candidates.items()
            )[:15]:
                self.stdout.write(
                    f"  {data['title']} ({slug})"
                )

            if not options["apply"]:
                self.stdout.write(
                    "PREVIEW ONLY — database unchanged."
                )
                continue

            created = 0
            existing = 0
            skipped = 0

            with transaction.atomic():
                for slug, values in candidates.items():
                    existing_place = Place.objects.filter(
                        slug=slug
                    ).first()

                    if existing_place is not None:
                        if existing_place.city_id != city.pk:
                            skipped += 1
                        else:
                            existing += 1
                        continue

                    _, was_created = Place.objects.get_or_create(
                        slug=slug,
                        defaults={
                            "city": city,
                            **values,
                            "category": None,
                            "owner": None,
                            "barangay": "",
                            "phone": "",
                            "email": "",
                            "is_active": False,
                            "is_verified": False,
                        }
                    )

                    if was_created:
                        created += 1
                    else:
                        existing += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"Created: {created} | "
                    f"Existing: {existing} | "
                    f"Other-city conflicts: {skipped}"
                )
            )

    @staticmethod
    def parse_elements(elements, city):
        candidates = {}

        for item in elements:
            if not isinstance(item, dict):
                continue

            tags = item.get("tags") or {}
            name = str(tags.get("name") or "").strip()
            osm_type = item.get("type")
            osm_id = item.get("id")

            if (
                not name
                or osm_type not in ("node", "way", "relation")
                or not isinstance(osm_id, int)
            ):
                continue

            coords = item.get("center") or item
            lat = coords.get("lat")
            lon = coords.get("lon")

            if lat is None or lon is None:
                continue

            try:
                lat = float(lat)
                lon = float(lon)
            except (TypeError, ValueError):
                continue

            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                continue

            slug = f"osm-{osm_type}-{osm_id}"

            website = str(
                tags.get("website")
                or tags.get("contact:website")
                or ""
            ).strip()

            if not website.lower().startswith(
                ("https://", "http://")
            ):
                website = ""

            title_max = (
                Place._meta.get_field("title").max_length
                or 200
            )
            address_max = (
                Place._meta.get_field("address").max_length
                or 255
            )
            website_max = (
                Place._meta.get_field("website").max_length
                or 200
            )

            candidates[slug] = {
                "title": name[:title_max],
                "description": str(
                    tags.get("description") or ""
                )[:3000],
                "address": str(
                    tags.get("addr:full")
                    or tags.get("addr:street")
                    or city.name
                )[:address_max],
                "latitude": lat,
                "longitude": lon,
                "website": website[:website_max],
            }

        return candidates

    @staticmethod
    def fetch(latitude, longitude, radius):
        clauses = "\n".join(
            f"nwr(around:{radius},"
            f"{latitude:.6f},{longitude:.6f})"
            f"{condition};"
            for condition in QUERY_FILTERS
        )

        query = (
            "[out:json][timeout:35];\n"
            "(\n"
            f"{clauses}\n"
            ");\n"
            "out center tags;"
        )

        payload = urlencode({
            "data": query
        }).encode("utf-8")

        context = ssl.create_default_context(
            cafile=certifi.where()
        )

        last_error = None

        for endpoint in OVERPASS_ENDPOINTS:
            try:
                request = Request(
                    endpoint,
                    data=payload,
                    headers={
                        "User-Agent":
                            "ExploreAnywhere/0.1 "
                            "(manual educational pilot)",
                        "Accept": "application/json",
                    }
                )

                with urlopen(
                    request,
                    timeout=55,
                    context=context
                ) as response:
                    data = json.load(response)

                elements = data.get("elements")

                if not isinstance(elements, list):
                    raise ValueError(
                        "Invalid Overpass response."
                    )

                return elements

            except (
                HTTPError,
                URLError,
                TimeoutError,
                ValueError,
                OSError,
            ) as error:
                last_error = error
                print(
                    f"Endpoint failed: {endpoint}\n"
                    f"Reason: {error}"
                )
                time.sleep(3)

        raise URLError(
            f"All endpoints failed: {last_error}"
        )
