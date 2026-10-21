from django.urls import path
from . import views
from .photo_preview import admin_photo_preview
from .city_discovery import city_discover

app_name = "places"

urlpatterns = [
    path("", views.attraction_carousel, name="attraction_carousel"),
    path("admin-photo-preview/", admin_photo_preview, name="admin_photo_preview"),
    path("discover/", city_discover, name="city_discover"),
    path("<int:pk>/", views.place_detail, name="place_detail"),
]
