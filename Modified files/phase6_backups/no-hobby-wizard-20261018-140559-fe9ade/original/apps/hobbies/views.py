
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.cities.models import City



HOBBIES = [
    {"id": "billiards", "label": "Billiards", "icon": ""},
    {"id": "basketball", "label": "Basketball", "icon": ""},
    {"id": "cafe", "label": "Café Hopping", "icon": ""},
    {"id": "hiking", "label": "Hiking", "icon": ""},
    {"id": "photography", "label": "Photography", "icon": ""},
    {"id": "gaming", "label": "Gaming", "icon": ""},
    {"id": "food", "label": "Food Trip", "icon": ""},
    {"id": "music", "label": "Music", "icon": ""},
    {"id": "culture", "label": "Art & Culture", "icon": ""},
    {"id": "nature", "label": "Beach & Nature", "icon": ""},
    {"id": "shopping", "label": "Shopping", "icon": ""},
    {"id": "others", "label": "Others", "icon": ""},
]


@login_required
@require_http_methods(["GET", "POST"])
def hobby_selection(request):
    # Kabankalan City is the only supported city.
    city = City.objects.get(
        pk=2,
        name__iexact="Kabankalan",
        province__iexact="Negros Occidental",
    )

    valid_ids = {hobby["id"] for hobby in HOBBIES}

    if request.method == "POST":
        chosen = request.POST.getlist("hobbies")

        chosen = list(dict.fromkeys(
            hobby for hobby in chosen
            if hobby in valid_ids
        ))

        if not chosen:
            return render(
                request,
                "hobbies/hobby_selection.html",
                {
                    "city": city,
                    "hobbies": HOBBIES,
                    "selected_hobbies": [],
                    "error": "Select at least one hobby.",
                },
            )

        request.session["selected_hobbies"] = chosen
        request.session["hobbies_city_id"] = city.pk

        return redirect("hobbies:search")

    selected = (
        request.session.get("selected_hobbies", [])
        if request.session.get("hobbies_city_id") == city.pk
        else []
    )

    return render(
        request,
        "hobbies/hobby_selection.html",
        {
            "city": city,
            "hobbies": HOBBIES,
            "selected_hobbies": selected,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def natural_language_search(request):
    # Always use Kabankalan.
    city = City.objects.get(
        pk=2,
        name__iexact="Kabankalan",
        province__iexact="Negros Occidental",
    )

    if (
        request.session.get("hobbies_city_id") != city.pk
        or not request.session.get("selected_hobbies")
    ):
        return redirect("hobbies:select")

    if request.method == "POST":
        query = request.POST.get(
            "query", ""
        ).strip()[:300]

        request.session[
            "attraction_search_query"
        ] = query

        return redirect(
            "places:attraction_carousel"
        )

    # Support the homepage search form, which uses GET and q.
    homepage_query = request.GET.get("q", "").strip()[:300]

    if homepage_query:
        request.session[
            "attraction_search_query"
        ] = homepage_query

        return redirect(
            "places:attraction_carousel"
        )

    return render(
        request,
        "hobbies/natural_language_search.html",
        {
            "city": city,
        },
    )
