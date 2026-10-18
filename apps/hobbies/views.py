
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
    """Legacy /hobbies/ route: Explore Places replaces the selection step."""
    from django.urls import reverse
    return redirect(reverse("places:attraction_carousel") + "?browse=all")


@login_required
@require_http_methods(["GET", "POST"])
def natural_language_search(request):
    """Legacy /hobbies/search/: preserve old search queries without a wizard."""
    from urllib.parse import urlencode
    from django.urls import reverse
    query = (
        request.POST.get("query") or request.POST.get("q") or ""
        if request.method == "POST"
        else request.GET.get("q") or request.GET.get("query") or ""
    ).strip()[:200]
    params = {"q": query} if query else {"browse": "all"}
    return redirect(reverse("places:attraction_carousel") + "?" + urlencode(params))

# exploreanywhere-phase6i-hobby-step-retired
