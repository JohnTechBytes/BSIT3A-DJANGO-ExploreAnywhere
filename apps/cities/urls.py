
from django.urls import path
from django.views.generic import RedirectView

from .views import (
    choose_city,
    api_provinces,
    api_cities,
)

urlpatterns = [
    # There is no city to pick: sessions are pinned to Kabankalan, so this
    # goes straight to the hobbies step. Named because places views redirect
    # here after resetting a session.
    path(
        "select/",
        RedirectView.as_view(pattern_name="hobbies:select", permanent=False),
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
