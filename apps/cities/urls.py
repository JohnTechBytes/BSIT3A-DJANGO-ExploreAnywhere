
from django.urls import path

from .views import (
    city_selection,
    choose_city,
    api_provinces,
    api_cities,
)

urlpatterns = [
    path(
        "select/",
        city_selection,
        name="city_selection",
    ),
    path(
        "select/choose/",
        choose_city,
        name="city_choose",
    ),
    path(
        "api/provinces/",
        api_provinces,
        name="api_provinces",
    ),
    path(
        "api/cities/",
        api_cities,
        name="api_cities",
    ),
]
