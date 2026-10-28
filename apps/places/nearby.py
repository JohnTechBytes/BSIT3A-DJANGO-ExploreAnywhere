"""Phase 6A: search verified Kabankalan records, calculate location only in browser.

Coordinates from the user's phone are NEVER posted to this view or stored.
"""
from urllib.parse import urlencode

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from apps.cities.models import City
from .models import Place
from .nearby_intent import SERVICE_CATEGORIES, detect_service_intent, matches_service


@login_required
@require_GET
def smart_search(request):
    """Homepage search: service questions -> Nearby, all other text -> discovery."""
    q = (request.GET.get("q") or "").strip()[:160]
    if not q:
        return redirect("places:attraction_carousel")
    # Keep homepage searches inside the unified discovery page.
    parameters = {"q": q}
    if detect_service_intent(q):
        parameters["mode"] = "nearby"
    return redirect(reverse("places:attraction_carousel") + "?" + urlencode(parameters))


@login_required
@require_GET
def nearby_places(request, *, unified=False):
    # Legacy bookmarks and old links remain valid without exposing a second
    # competing discovery page. Retain q/service/place/origin parameters.
    if not unified:
        parameters = request.GET.copy()
        parameters["mode"] = "nearby"
        return redirect(
            reverse("places:attraction_carousel") + "?" + parameters.urlencode()
        )

    city = City.objects.filter(
        pk=2, name__iexact="Kabankalan", province__iexact="Negros Occidental",
    ).first()
    if city is None:
        return redirect("city_selection")

    query = (request.GET.get("q") or "").strip()[:160]
    selected_service = (request.GET.get("service") or "").strip()
    valid_services = dict(SERVICE_CATEGORIES)
    if selected_service not in valid_services:
        selected_service = detect_service_intent(query) or ""

    # Enforce publication AND city checks on every read, independently of session.
    published = (Place.objects.filter(
        city=city, is_active=True, is_verified=True,
    ).select_related("category").prefetch_related("hobbies").order_by("title", "pk"))

    # Explicit suggestions and exact-name searches take priority over a generic
    # service intent. A business named "Coffee & Talk" must not return all cafes.
    # Every branch begins from the same independently publication-checked queryset.
    selected_place_key = (request.GET.get("place") or "").strip()[:15]
    if selected_place_key.isascii() and selected_place_key.isdecimal():
        selected_service = ""
        matched = published.filter(pk=int(selected_place_key))
    elif query:
        exact = list(published.filter(title__iexact=query)[:20])
        if exact:
            matched = iter(exact)
            selected_service = ""
        elif selected_service:
            matched = (place for place in published if matches_service(place, selected_service))
        else:
            from .views import build_attraction_filter
            predicate = build_attraction_filter(query)
            if predicate is not None:
                published = published.filter(predicate).distinct()
            matched = iter(published)
    elif selected_service:
        matched = (place for place in published if matches_service(place, selected_service))
    else:
        matched = iter(published)

    # Limit only the display; avoid falsely claiming "all nearest" when capped.
    MAX_RESULTS = 250
    results = []
    limit_reached = False
    for place in matched:
        if len(results) >= MAX_RESULTS:
            limit_reached = True
            break
        results.append(place)

    # Suggestions are real, publicly approved listings, never imported candidates.
    # Only minimal display fields are embedded; no private account data or GPS.
    approved_suggestions = list(Place.objects.filter(
        city=city, is_active=True, is_verified=True,
    ).order_by("title", "pk").values("pk", "title", "category__name")[:250])

    # ExploreAnywhere Phase 6K: curated Kabankalan reference landmarks
    # The fallback must not become a dropdown of every future business.
    # These are previously published Kabankalan destinations; only records
    # that remain independently verified, active, and mapped are selectable.
    # Kabankalan Plaza will appear automatically once its coordinates are verified.
    kabankalan_landmark_names = (
        "Kabankalan Plaza", "CPSU Museum", "Mag Aso Falls", "Amyan Hill",
        "Maronggues Hill", "Mount Luyang", "Mount Nai-guin",
    )
    landmarks = list(Place.objects.filter(
        city=city, is_verified=True, is_active=True,
        title__in=kabankalan_landmark_names,
        latitude__isnull=False, longitude__isnull=False,
    ))
    priority = {name.casefold(): idx for idx, name in enumerate(kabankalan_landmark_names)}
    landmarks.sort(key=lambda place: priority.get(place.title.casefold(), 100))
    requested_origin = (request.GET.get("origin") or "").strip()
    selected_origin = next(
        (place for place in landmarks if str(place.pk) == requested_origin), None,
    )

    return render(request, "places/nearby_places.html", {
        "selected_city": city,
        "query": query,
        "selected_service": selected_service,
        "selected_service_label": valid_services.get(selected_service, ""),
        "service_categories": SERVICE_CATEGORIES,
        "results": results,
        "result_count": len(results),
        "limit_reached": limit_reached,
        "approved_suggestions": approved_suggestions,
        "landmarks": landmarks,
        "selected_origin": selected_origin,
        "active_discovery_mode": "nearby",
    })
