
from math import ceil

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
)
from django.views.decorators.http import require_GET, require_POST

from .locking import locked_cities, locked_city


PAGE_SIZE = 24


@require_GET
@login_required
def api_provinces(request):
    # This site serves one city, so it exposes one province.
    city = locked_city()
    province = city.province_ref if city is not None else None

    if province is None:
        return JsonResponse({"provinces": []})

    return JsonResponse({
        "provinces": [
            {
                "name": province.name,
                "slug": province.slug,
                "region": province.region,
                "psgc_code": province.psgc_code,
            }
        ]
    })


@require_GET
@login_required
def api_cities(request):
    slug = request.GET.get("province", "").strip()
    query = request.GET.get("q", "").strip()[:100]

    try:
        page = max(
            1,
            int(request.GET.get("page", "1"))
        )
    except ValueError:
        page = 1

    if not slug:
        return JsonResponse({
            "error": "province is required"
        }, status=400)

    # Never list cities beyond the one this site serves, whatever was asked for.
    city = locked_city()
    province = city.province_ref if city is not None else None

    if province is None or slug != province.slug:
        return JsonResponse({
            "province": province.name if province else "",
            "region": province.region if province else "",
            "cities": [],
            "page": 1,
            "page_size": PAGE_SIZE,
            "total": 0,
            "has_next": False,
        })

    queryset = locked_cities()

    if query:
        queryset = queryset.filter(
            name__icontains=query
        )

    queryset = queryset.order_by("name", "pk")

    total = queryset.count()
    pages = ceil(total / PAGE_SIZE)
    offset = (page - 1) * PAGE_SIZE

    page_cities = list(
        queryset[offset:offset + PAGE_SIZE]
    )

    Place = apps.get_model("places", "Place")

    page_ids = [city.pk for city in page_cities]

    place_fields = {
        f.name for f in Place._meta.fields
    }

    filters = {"city_id__in": page_ids}

    if "status" in place_fields:
        filters["status"] = "active"
    elif "is_active" in place_fields:
        filters["is_active"] = True

    counts = dict(
        Place.objects.filter(**filters)
        .values("city_id")
        .annotate(total=Count("pk"))
        .values_list("city_id", "total")
    )

    results = []

    for city in page_cities:
        active = city.status == "active"

        results.append({
            "id": city.pk,
            "name": city.name,
            "kind": city.kind,
            "province": province.name,
            "region": province.region,
            "status": city.status,
            "active": active,
            "places_count": counts.get(city.pk, 0),
        })

    return JsonResponse({
        "province": province.name,
        "region": province.region,
        "cities": results,
        "page": page,
        "page_size": PAGE_SIZE,
        "total": total,
        "has_next": page < pages,
    })


@login_required
@require_POST
def choose_city(request):
    raw_id = request.POST.get("city_id", "").strip()
    city = get_object_or_404(locked_cities())

    # Reject anything the middleware would silently replace next request.
    if not raw_id.isdigit() or int(raw_id) != city.pk:
        messages.error(
            request,
            "ExploreKabankalan covers Kabankalan City only.",
        )
        return redirect("city_selection")

    request.session["city_id"] = city.pk
    request.session["selected_city_id"] = city.pk
    request.session["selected_city_name"] = city.name
    request.session["selected_province"] = city.province

    request.session.pop("selected_hobbies", None)
    request.session.pop("hobbies_city_id", None)
    request.session.pop("attraction_search_query", None)

    messages.success(
        request,
        f"Welcome to {city.name}! Explore attractions in this city."
    )

    return redirect("places:city_discover")


