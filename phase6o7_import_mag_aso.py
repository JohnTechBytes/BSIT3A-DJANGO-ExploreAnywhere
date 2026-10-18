"""One-place Phase 6O.7 importer. Run from Django manage.py shell.

Defines import_mag_aso(preview_only=True). Calling it with False is an
explicit database write, limited to Kabankalan Place PK 1703.
Does not update any other Place, or alter publication / verification fields.
"""

from django.db import connection, transaction
from django.db.models import Q
from apps.cities.models import City
from apps.places.models import Place
from apps.places.management.commands.phase6o_business_photos import (
    CITY_ID, eligible, load_csv, clean_text,
)
from urllib.parse import urlsplit

PLACE_ID = 1703
PLACE_SLUG = "osm-node-3369728379"
PLACE_NAME = "Mag Aso Falls"
EXPECTED_FILE = "/wikipedia/commons/4/4e/Mag-asoFallsKabankalanNegrosOcc.jpg"
EXPECTED_SOURCE = "https://commons.wikimedia.org/wiki/File:Mag-asoFallsKabankalanNegrosOcc.jpg"
EXPECTED_LICENSE = "CC BY-SA 4.0"
EXPECTED_LICENSE_URL = "https://creativecommons.org/licenses/by-sa/4.0"
EXPECTED_CREATOR = "Godopeta7410"


def import_mag_aso(*, preview_only=True):
    """Preview by default; write only for an explicit preview_only=False call."""
    if connection.vendor != "mysql":
        raise RuntimeError("Expected a MySQL/MariaDB database. No changes made.")

    city = City.objects.filter(pk=CITY_ID).first()
    if city is None or city.name.strip().casefold() != "kabankalan":
        raise RuntimeError("Kabankalan is not City ID 2. No changes made.")

    rows = load_csv()
    if rows is None:
        raise RuntimeError("Phase 6O review CSV is missing. No changes made.")
    matches = [row for row in rows if (row.get("place_id") or "").strip() == str(PLACE_ID)]
    if len(matches) != 1:
        raise RuntimeError("Expected exactly one Place 1703 CSV review row. No changes made.")
    row = matches[0]

    # Match not just the license type, but this specific Commons file and author.
    image = urlsplit((row.get("image_url") or "").strip())
    source = (row.get("source_url") or "").strip()
    license_url = (row.get("license_url") or "").strip().rstrip("/")
    checks = {
        "place_name": row.get("place_name") == PLACE_NAME,
        "place_slug": row.get("place_slug") == PLACE_SLUG,
        "CSV says existing cover is absent": row.get("already_has_cover") == "no",
        "Wikimedia image hostname": image.scheme == "https" and image.hostname == "upload.wikimedia.org",
        "exact Wikimedia image file": image.path == EXPECTED_FILE,
        "exact Commons source": source == EXPECTED_SOURCE,
        "exact photographer": (row.get("credit") or "").strip() == EXPECTED_CREATOR,
        "exact license": (row.get("license") or "").strip() == EXPECTED_LICENSE,
        "exact license link": license_url == EXPECTED_LICENSE_URL,
        "admin approval": (row.get("review_decision") or "").strip().lower() == "approve",
        "identity checked": (row.get("identity_checked") or "").strip().lower() == "yes",
        "rights checked": (row.get("rights_checked") or "").strip().lower() == "yes",
        "review notes": bool((row.get("review_notes") or "").strip()),
    }
    failures = [key for key, value in checks.items() if not value]
    if failures:
        raise RuntimeError("Review verification failed: " + ", ".join(failures) + ". No changes made.")

    with transaction.atomic():
        qs = Place.objects.filter(pk=PLACE_ID, city_id=CITY_ID, slug=PLACE_SLUG)
        place = (qs.select_for_update().get() if not preview_only else qs.get())
        problems = eligible(row, place)  # Reuses your existing Phase 6O approval rules.
        if problems:
            raise RuntimeError("Importer refused: " + "; ".join(problems) + ". No changes made.")

        values = {
            "cover_image_url": (row["image_url"] or "").strip(),
            "photo_credit": clean_text(row["credit"], 500),
            "photo_source_url": source,
            "photo_license": EXPECTED_LICENSE,
            "photo_license_url": (row["license_url"] or "").strip(),
        }
        publication_before = (place.is_active, place.is_verified)
        print("TARGET:", PLACE_ID, "|", PLACE_NAME, "|", PLACE_SLUG)
        print("DATABASE:", connection.settings_dict.get("NAME"))
        print("PHOTO:", values["photo_source_url"])
        print("ATTRIBUTION:", values["photo_credit"], "|", values["photo_license"])
        if preview_only:
            print("GUARDED PREVIEW PASS: exactly 1 specified row eligible. Database unchanged.")
            return

        # Query deliberately scopes by BOTH numeric PK and city/OSM identity.
        changed = (qs.filter(Q(cover_image="") | Q(cover_image__isnull=True))
                   .filter(Q(cover_image_url="") | Q(cover_image_url__isnull=True))
                   .update(**values))
        if changed != 1:
            raise RuntimeError("Expected to update exactly one target record; transaction rolled back.")

        reloaded = Place.objects.get(pk=PLACE_ID, city_id=CITY_ID, slug=PLACE_SLUG)
        if any(getattr(reloaded, key) != value for key, value in values.items()):
            raise RuntimeError("Post-write metadata mismatch; transaction rolled back.")
        if (reloaded.is_active, reloaded.is_verified) != publication_before:
            raise RuntimeError("Publication/verification status changed; transaction rolled back.")

    print("APPLIED: exactly 1 cover photo, only Place ID 1703. Transaction committed.")
    print("Attribution metadata verified. Publication/verification unchanged.")
