"""The single city this site serves.

KabankalanOnlyMiddleware pins every session to this city. Anything that lists
or accepts a city must go through these helpers, otherwise it offers a choice
the middleware silently discards on the next request.
"""

from .models import City

LOCKED_CITY_PK = 2
LOCKED_CITY_NAME = "Kabankalan"
LOCKED_CITY_PROVINCE = "Negros Occidental"


def locked_cities():
    """Queryset containing only the city this site is locked to."""
    return City.objects.filter(
        pk=LOCKED_CITY_PK,
        name__iexact=LOCKED_CITY_NAME,
        province__iexact=LOCKED_CITY_PROVINCE,
    )


def locked_city():
    """The locked city, or None when the row is missing."""
    return locked_cities().first()
