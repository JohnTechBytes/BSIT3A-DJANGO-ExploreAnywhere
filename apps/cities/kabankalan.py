
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q

from apps.cities.models import City
from apps.places.models import Place


def get_kabankalan_city():
    cities = list(
        City.objects.filter(
            name__icontains="Kabankalan"
        ).filter(
            Q(province_ref__name__iexact="Negros Occidental")
            | Q(province__iexact="Negros Occidental")
        )[:2]
    )

    if len(cities) != 1:
        raise ImproperlyConfigured(
            "Expected exactly one Kabankalan City record "
            "in Negros Occidental. Check the cities database."
        )

    return cities[0]


def kabankalan_places():
    """Base queryset for Kabankalan-only discovery."""
    return Place.objects.filter(
        city=get_kabankalan_city()
    )


def public_kabankalan_places():
    """Approved Kabankalan recommendations."""
    return kabankalan_places().filter(
        is_active=True,
        is_verified=True,
    )
