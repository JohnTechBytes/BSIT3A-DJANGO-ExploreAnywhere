from django.urls import path
from .selection_views import select_city, choose_city

urlpatterns = [
    path("", select_city, name="city_selection"),
    path("choose/", choose_city, name="city_choose"),
]
