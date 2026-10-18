"""Kabankalan itinerary routes — Phase 3D."""
from django.urls import path
from . import views

app_name = "itineraries"

urlpatterns = [
    path("", views.my_itineraries, name="list"),
    path("new/", views.create_itinerary, name="create"),
    path("<int:pk>/", views.builder, name="builder"),
    path("<int:pk>/update/", views.update_itinerary, name="update"),
    path("<int:pk>/delete/", views.delete_itinerary, name="delete"),
    path("<int:pk>/stops/add/", views.add_stop, name="add_stop"),
    path("<int:pk>/stops/<int:stop_id>/update/", views.update_stop, name="update_stop"),
    path("<int:pk>/stops/<int:stop_id>/remove/", views.remove_stop, name="remove_stop"),
    path("<int:pk>/stops/<int:stop_id>/move/", views.move_stop, name="move_stop"),
]
