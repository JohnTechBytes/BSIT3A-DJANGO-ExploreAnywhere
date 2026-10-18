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
    target = "places:nearby_places" if detect_service_intent(q) else "places:attraction_carousel"
    return redirect(reverse(target) + "?" + urlencode({"q": q}))


@login_required
@require_GET
def nearby_places(request):
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

    # Existing recommendation scoring does not affect distance ranking.
    if selected_service:
        matched = (place for place in published if matches_service(place, selected_service))
    elif query:
        from .views import build_attraction_filter
        predicate = build_attraction_filter(query)
        if predicate is not None:
            published = published.filter(predicate).distinct()
        matched = iter(published)
    else:
        matched = iter(published)

    # Bound initial HTML for city-scale performance. Do not claim nearest across
    # records not rendered; the UI exposes this limit if reached.
    MAX_RESULTS = 250
    results = []
    for place in matched:
        if len(results) == MAX_RESULTS:
            break
        results.append(place)

    # Only real verified point records can be reference locations.
    landmarks = list(Place.objects.filter(
        city=city, is_verified=True, is_active=True,
        latitude__isnull=False, longitude__isnull=False,
    ).order_by("title", "pk")[:100])
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
        "limit_reached": len(results) == MAX_RESULTS,
        "landmarks": landmarks,
        "selected_origin": selected_origin,
    })
