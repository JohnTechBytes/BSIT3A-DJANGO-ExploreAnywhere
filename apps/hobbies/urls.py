
from django.urls import path
from . import views

app_name = "hobbies"

urlpatterns = [
    path(
        "",
        views.hobby_selection,
        name="select",
    ),
    path(
        "search/",
        views.natural_language_search,
        name="search",
    ),
]
