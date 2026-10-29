"""Routes of the public usability evaluation module."""

from django.urls import path

from . import views

app_name = "evaluation"

urlpatterns = [
    path("sus/", views.sus_survey, name="sus_survey"),
    path("sus/thanks/", views.sus_thanks, name="sus_thanks"),
]
