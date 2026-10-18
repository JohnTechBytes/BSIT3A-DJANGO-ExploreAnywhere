
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
django.setup()

from django.db import transaction
from apps.cities.models import City
from apps.places.models import Place


def main():
    city = City.objects.get(pk=2)

    # This OSM identifier came from your successful preview.
    # Coordinates and detailed attributes are not invented.
    osm_slug = "osm-way-247293144"

    with transaction.atomic():
        place, created = Place.objects.get_or_create(
            slug=osm_slug,
            defaults={
                "city": city,
                "title": "Kabankalan Plaza",
                "description": (
                    "Public plaza in Kabankalan. "
                    "Imported from an OpenStreetMap search; "
                    "details require administrator verification."
                ),
                "address": "Kabankalan, Negros Occidental",
                "barangay": "",
                "latitude": None,
                "longitude": None,
                "phone": "",
                "website": "",
                "email": "",
                "category": None,
                "owner": None,
                "is_verified": False,
                "is_active": False,
            },
        )

    print()
    print("STATUS:", "CREATED" if created else "ALREADY EXISTS")
    print("PLACE ID:", place.pk)
    print("PLACE:", place.title)
    print("CITY:", place.city.name)
    print("VERIFIED:", place.is_verified)
    print("ACTIVE:", place.is_active)


if __name__ == "__main__":
    main()
