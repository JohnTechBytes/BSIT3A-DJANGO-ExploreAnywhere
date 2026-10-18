from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.cities.models import City


# Approximate city-center coordinates for development.
# Verify coordinates before using them for precise navigation.
CITIES = [
    ("Bacolod", "Negros Occidental", "10.6765", "122.9509"),
    ("Kabankalan", "Negros Occidental", "9.9889", "122.8142"),
    ("Silay", "Negros Occidental", "10.8000", "122.9770"),
    ("Bago", "Negros Occidental", "10.5333", "122.8333"),
    ("Sipalay", "Negros Occidental", "9.7540", "122.4030"),
    ("Iloilo City", "Iloilo", "10.7202", "122.5621"),
    ("Passi City", "Iloilo", "11.1075", "122.6414"),
    ("Cebu City", "Cebu", "10.3157", "123.8854"),
    ("Mandaue City", "Cebu", "10.3333", "123.9333"),
    ("Lapu-Lapu City", "Cebu", "10.3100", "123.9490"),
    ("Digos City", "Davao del Sur", "6.7490", "125.3570"),
]


class Command(BaseCommand):
    help = "Create starter cities grouped by province."

    def handle(self, *args, **kwargs):
        created = 0

        for name, province, lat, lng in CITIES:
            if City.objects.filter(
                name__iexact=name
            ).exists():
                continue

            slug = slugify(name)

            if City.objects.filter(slug=slug).exists():
                continue

            City.objects.create(
                name=name,
                slug=slug,
                province=province,
                country="Philippines",
                status=City.Status.ACTIVE,
                latitude=lat,
                longitude=lng,
            )

            created += 1

        total = City.objects.filter(
            status=City.Status.ACTIVE
        ).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Added {created} cities. Active cities: {total}"
            )
        )
