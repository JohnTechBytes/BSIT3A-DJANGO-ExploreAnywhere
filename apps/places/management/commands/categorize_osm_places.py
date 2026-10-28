
import csv
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.places.models import Place


# Explicit OSM types only. Generic "attraction" and
# "information" records are intentionally excluded.
OSM_CATEGORY_MAP = {
    ("natural", "beach"): ("Beach", "beach"),
    ("natural", "peak"): ("Mountain & Peak", "mountain-peak"),
    ("natural", "spring"): ("Spring", "spring"),
    ("natural", "hot_spring"): ("Hot Spring", "hot-spring"),
    ("natural", "cave_entrance"): ("Cave", "cave"),

    ("tourism", "viewpoint"): ("Scenic Viewpoint", "scenic-viewpoint"),
    ("tourism", "museum"): ("Museum", "museum"),
    ("tourism", "artwork"): ("Public Art", "public-art"),
    ("tourism", "gallery"): ("Art Gallery", "art-gallery"),
    ("tourism", "zoo"): ("Zoo", "zoo"),
    ("tourism", "theme_park"): ("Theme Park", "theme-park"),
    ("tourism", "aquarium"): ("Aquarium", "aquarium"),

    ("historic", "memorial"): ("Memorial", "memorial"),
    ("historic", "monument"): ("Monument", "monument"),
    ("historic", "ruins"): ("Historic Ruins", "historic-ruins"),
    ("historic", "wayside_shrine"): ("Shrine", "shrine"),
    ("historic", "fort"): ("Historic Fort", "historic-fort"),
    ("historic", "archaeological_site"): (
        "Archaeological Site", "archaeological-site"
    ),
    ("historic", "castle"): ("Historic Castle", "historic-castle"),

    ("leisure", "park"): ("Park", "park"),
    ("leisure", "garden"): ("Garden", "garden"),
    ("leisure", "nature_reserve"): (
        "Nature Reserve", "nature-reserve"
    ),
}


class Command(BaseCommand):
    help = "Categorize imported OSM places. Preview by default."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Save the proposed category assignments.",
        )
        parser.add_argument(
            "--csv",
            default="data/osm/extracted/philippines_attractions_nodes.csv",
            help="Path to the original OSM extraction CSV.",
        )

    def handle(self, *args, **options):
        csv_path = Path(options["csv"])

        if not csv_path.is_file():
            raise CommandError(
                f"OSM CSV not found: {csv_path}"
            )

        # Build exact OSM ID -> category mapping.
        osm_categories = {}
        duplicate_ids = set()

        with csv_path.open(
            newline="", encoding="utf-8-sig"
        ) as file:
            reader = csv.DictReader(file)

            required = {"osm_id", "category", "subcategory"}
            if not required.issubset(reader.fieldnames or []):
                raise CommandError(
                    f"CSV must include: {sorted(required)}"
                )

            for row in reader:
                osm_id = (row["osm_id"] or "").strip()

                if not osm_id:
                    continue

                key = (
                    (row["category"] or "").strip().lower(),
                    (row["subcategory"] or "").strip().lower(),
                )

                category_info = OSM_CATEGORY_MAP.get(key)

                if not category_info:
                    continue

                if osm_id in osm_categories:
                    duplicate_ids.add(osm_id)
                else:
                    osm_categories[osm_id] = category_info

        # Ambiguous duplicate OSM IDs must not be assigned.
        for osm_id in duplicate_ids:
            osm_categories.pop(osm_id, None)

        proposals = []
        counts = Counter()
        total_imported = 0
        already_categorized = 0
        unmatched = 0

        places = Place.objects.filter(
            slug__startswith="osm-"
        ).only("id", "slug", "category_id")

        for place in places.iterator(chunk_size=1000):
            total_imported += 1

            if place.category_id is not None:
                already_categorized += 1
                continue

            category_info = osm_categories.get(place.slug)

            if category_info is None:
                unmatched += 1
                continue

            proposals.append((place.pk, category_info))
            counts[category_info[0]] += 1

        self.stdout.write(
            f"Imported places checked: {total_imported}"
        )
        self.stdout.write(
            f"Already categorized: {already_categorized}"
        )
        self.stdout.write(
            f"Not classifiable from mapped OSM types: {unmatched}"
        )
        self.stdout.write(
            f"Proposed category assignments: {len(proposals)}"
        )

        for name, count in counts.most_common():
            self.stdout.write(f"  {name}: {count}")

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW ONLY. No database changes made."
                )
            )
            self.stdout.write(
                "Run with --apply to save assignments."
            )
            return

        # Use the Category model already connected to Place.
        Category = Place._meta.get_field(
            "category"
        ).remote_field.model

        changed = 0

        with transaction.atomic():
            category_cache = {}

            for name, slug in sorted(set(
                info for _, info in proposals
            )):
                category, created = Category.objects.get_or_create(
                    slug=slug,
                    defaults={"name": name},
                )
                category_cache[slug] = category

            # Recheck category=None before updating, so
            # manually categorized places are not overwritten.
            for place_id, (name, slug) in proposals:
                updated = Place.objects.filter(
                    pk=place_id,
                    category__isnull=True,
                ).update(
                    category=category_cache[slug]
                )
                changed += updated

        self.stdout.write(
            self.style.SUCCESS(
                f"SUCCESS: Categorized {changed} attractions."
            )
        )
        self.stdout.write(
            "Publication, verification, and city fields unchanged."
        )
