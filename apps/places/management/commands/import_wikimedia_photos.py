
import csv
import html
from pathlib import Path
from urllib.parse import urlsplit

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.html import strip_tags

from apps.places.models import Place


CSV_FILE = Path(
    "data/osm/validation/wikimedia_photo_candidates.csv"
)

ALLOWED_LICENSES = {
    "CC BY 4.0",
    "CC BY-SA 4.0",
    "CC BY-SA 3.0",
}


def safe_https_url(value, domains):
    value = (value or "").strip()

    try:
        parsed = urlsplit(value)
    except ValueError:
        return False

    return (
        parsed.scheme == "https"
        and (parsed.hostname or "").lower() in domains
        and not parsed.username
        and not parsed.password
    )


class Command(BaseCommand):
    help = "Preview or import Wikimedia attraction photos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Save eligible photos to MySQL.",
        )

    def handle(self, *args, **options):
        if not CSV_FILE.is_file():
            raise CommandError(
                f"Photo report not found: {CSV_FILE}"
            )

        eligible = []
        skipped = []

        with CSV_FILE.open(
            encoding="utf-8-sig",
            newline=""
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                osm_id = (row.get("osm_id") or "").strip()
                name = (row.get("name") or "").strip()
                license_name = (
                    row.get("license") or ""
                ).strip()

                artist = html.unescape(
                    strip_tags(row.get("artist") or "")
                ).strip()

                image_url = (
                    row.get("image_url") or ""
                ).strip()

                source_url = (
                    row.get("source_url") or ""
                ).strip()

                license_url = (
                    row.get("license_url") or ""
                ).strip()

                place = Place.objects.filter(
                    slug=osm_id
                ).first()

                reasons = []

                if not place:
                    reasons.append("OSM ID not found")

                if not name:
                    reasons.append("Missing attraction name")

                if place and name:
                    if place.title.casefold() != name.casefold():
                        reasons.append("Name mismatch")

                if not artist:
                    reasons.append("Missing photographer credit")

                if license_name not in ALLOWED_LICENSES:
                    reasons.append("Unsupported license")

                if not safe_https_url(
                    image_url,
                    {
                        "upload.wikimedia.org",
                        "thumb.wikimedia.org",
                    },
                ):
                    reasons.append("Invalid image URL")

                if not safe_https_url(
                    source_url,
                    {"commons.wikimedia.org"},
                ):
                    reasons.append("Invalid Commons URL")

                if not safe_https_url(
                    license_url,
                    {"creativecommons.org"},
                ):
                    reasons.append("Invalid license URL")

                if place and (
                    place.cover_image
                    or place.cover_image_url
                ):
                    reasons.append("Existing image preserved")

                if reasons:
                    skipped.append(
                        (name or osm_id, ", ".join(reasons))
                    )
                    continue

                eligible.append({
                    "place_id": place.pk,
                    "name": name,
                    "image_url": image_url,
                    "artist": artist[:500],
                    "source_url": source_url,
                    "license": license_name,
                    "license_url": license_url,
                })

        self.stdout.write(
            f"Eligible photos: {len(eligible)}"
        )

        for item in eligible:
            self.stdout.write(
                f"  READY: {item['name']} "
                f"— {item['license']}"
            )

        for name, reason in skipped:
            self.stdout.write(
                f"  SKIPPED: {name} — {reason}"
            )

        if not options["apply"]:
            self.stdout.write(
                self.style.WARNING(
                    "PREVIEW ONLY. MySQL was not modified."
                )
            )
            return

        updated = 0

        with transaction.atomic():
            for item in eligible:
                count = (
                    Place.objects
                    .filter(pk=item["place_id"])
                    .filter(
                        Q(cover_image="")
                        | Q(cover_image__isnull=True)
                    )
                    .filter(
                        Q(cover_image_url="")
                        | Q(cover_image_url__isnull=True)
                    )
                    .update(
                        cover_image_url=item["image_url"],
                        photo_credit=item["artist"],
                        photo_source_url=item["source_url"],
                        photo_license=item["license"],
                        photo_license_url=item["license_url"],
                    )
                )

                updated += count

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {updated} attraction photos."
            )
        )
