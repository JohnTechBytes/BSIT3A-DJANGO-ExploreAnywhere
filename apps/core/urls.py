"""Routes of the core application."""

from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("privacy/", views.privacy_notice, name="privacy_notice"),
]
