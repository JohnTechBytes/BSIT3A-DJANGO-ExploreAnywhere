
from django.core.exceptions import ImproperlyConfigured

from apps.cities.models import City


class KabankalanOnlyMiddleware:
    """
    Lock visitor sessions to Kabankalan City.

    This does not delete nationwide records from MySQL.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.city_id = None

    def __call__(self, request):
        if self.city_id is None:
            city = City.objects.filter(
                pk=2,
                name__iexact="Kabankalan",
                province__iexact="Negros Occidental",
            ).first()

            if city is None:
                raise ImproperlyConfigured(
                    "Kabankalan City (ID 2) was not found."
                )

            self.city_id = city.pk

        session = request.session

        if (
            session.get("city_id") != self.city_id
            or session.get("selected_city_id") != self.city_id
            or session.get("selected_city_name") != "Kabankalan"
            or session.get("selected_province") != "Negros Occidental"
        ):
            session["city_id"] = self.city_id
            session["selected_city_id"] = self.city_id
            session["selected_city_name"] = "Kabankalan"
            session["selected_province"] = "Negros Occidental"

        return self.get_response(request)
