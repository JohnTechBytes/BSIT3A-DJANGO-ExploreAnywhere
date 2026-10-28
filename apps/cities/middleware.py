from django.core.exceptions import ImproperlyConfigured

from .locking import locked_city


class KabankalanOnlyMiddleware:
    """Lock every visitor session to the one city this site serves.

    Nationwide records stay in MySQL; this only constrains sessions.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.city = None

    def __call__(self, request):
        if self.city is None:
            self.city = locked_city()

            if self.city is None:
                raise ImproperlyConfigured(
                    "Kabankalan City (ID 2) was not found."
                )

        expected = {
            "city_id": self.city.pk,
            "selected_city_id": self.city.pk,
            "selected_city_name": self.city.name,
            "selected_province": self.city.province,
        }

        session = request.session

        if any(session.get(key) != value for key, value in expected.items()):
            session.update(expected)

        return self.get_response(request)
