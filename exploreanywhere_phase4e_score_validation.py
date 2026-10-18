#!/usr/bin/env python3
"""ExploreAnywhere Phase 4E - read-only recommendation score validation.

Run from the Django project root with the project's venv Python.
Does not modify files, database records, migrations, or call external APIs.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

CITY_ID = 2
TEST_CASES = [
    ("Hiking + Photography", ["hiking", "photography"]),
    ("Nature", ["nature"]),
    ("Art & Culture", ["culture"]),
    ("Cafe Hopping", ["cafe"]),
    ("No hobbies selected", []),
]


def main() -> int:
    project = Path.cwd()
    if not (project / "manage.py").is_file():
        print("ERROR: Open PowerShell in the ExploreAnywhere project root (the folder containing manage.py).")
        return 2

    sys.path.insert(0, str(project))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
    try:
        import django
        django.setup()
        from django.db import connection
        from apps.places.models import Place
        from apps.places.recommendations import rank_kabankalan_places
    except Exception as exc:
        print(f"ERROR: Could not start Django or import the recommendation engine: {type(exc).__name__}: {exc}")
        return 2

    print("=" * 72)
    print("EXPLOREANYWHERE — PHASE 4E READ-ONLY SCORE VALIDATION")
    print("=" * 72)
    print("Django project:", project)
    print("Filters: city_id=2, is_active=True, is_verified=True")
    print("No records, code, keys, or migrations will be changed.")

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        places = list(
            Place.objects.filter(city_id=CITY_ID, is_active=True, is_verified=True)
            .select_related("category", "city")
            .prefetch_related("hobbies")
        )
    except Exception as exc:
        print(f"ERROR: Database query failed: {type(exc).__name__}: {exc}")
        return 2

    print("\nPublished Kabankalan destinations:", len(places))
    print("\n1. HOBBY ASSIGNMENTS AND RATING AVAILABILITY")
    for place in sorted(places, key=lambda p: p.title.lower()):
        hobbies = ", ".join(sorted(h.slug for h in place.hobbies.all())) or "NONE"
        ratings = f"{place.avg_rating}/5 ({place.review_count} reviews)" if place.review_count and place.avg_rating is not None else "no usable rating"
        photo = bool(place.cover_image or place.cover_image_url)
        desc = bool((place.description or "").strip())
        coords = place.latitude is not None and place.longitude is not None
        print(f"  {place.title}: hobbies=[{hobbies}] | rating={ratings} | photo={photo} | description={desc} | coordinates={coords}")

    print("\n2. LIVE RECOMMENDATION FUNCTION OUTPUT")
    for label, selections in TEST_CASES:
        print(f"\n  Scenario: {label} (selected={selections})")
        try:
            result = rank_kabankalan_places(list(places), selections)
            if not isinstance(result, (list, tuple)):
                result = list(result)
            for p in result:
                score = getattr(p, "match_percent", None)
                matched = getattr(p, "matched_hobbies", [])
                issue = " [CHECK SCORE]" if not isinstance(score, (int, float)) or not 0 <= score <= 100 else ""
                print(f"    {str(score).rjust(3)}%  {p.title} | matching hobbies: {', '.join(matched) or 'none'}{issue}")
        except Exception as exc:
            print(f"  ERROR while ranking {label}: {type(exc).__name__}: {exc}")
            return 1

    print("\n3. WARNINGS TO REVIEW")
    no_hobbies = [p.title for p in places if not p.hobbies.all()]
    no_coords = [p.title for p in places if p.latitude is None or p.longitude is None]
    no_desc = [p.title for p in places if not (p.description or "").strip()]
    print("  No assigned hobbies:", ", ".join(no_hobbies) or "none")
    print("  Missing coordinates:", ", ".join(no_coords) or "none")
    print("  Missing descriptions:", ", ".join(no_desc) or "none")
    print("  Reminder: Recommendation Match may normalize available weights.")
    print("  A high displayed score does NOT prove that GPS distance was considered.")
    print("  A zero score for unselected hobbies needs a clear UI empty-selection explanation.")
    print("\nDONE: Read-only QA complete. Send this output to ChatGPT.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
