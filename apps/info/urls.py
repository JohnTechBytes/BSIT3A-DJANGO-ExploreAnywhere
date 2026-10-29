"""Routes of the City Information module.

The legacy Info CRUD routes stay disabled: they referenced a model that no
longer exists. The public page below replaces them with a read-only view of
the published ``CityInformation`` records.
"""

from django.urls import path

from . import views

app_name = "info"

urlpatterns = [
    path("", views.city_information, name="city_information"),
]
