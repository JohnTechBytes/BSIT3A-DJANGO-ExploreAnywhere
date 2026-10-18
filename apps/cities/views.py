
from math import ceil

from django.apps import apps
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Count, Q
from django.http import JsonResponse
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import NoReverseMatch, reverse
from django.views.decorators.http import require_GET, require_POST

from .models import City, Province


PAGE_SIZE = 24


def _active_place_counts():
    Place = apps.get_model("places", "Place")

    field_names = {
        f.name for f in Place._meta.fields
    }

    if "city" not in field_names:
        return {}

    filters = {}

    if "status" in field_names:
        filters["status"] = "active"
    elif "is_active" in field_names:
        filters["is_active"] = True

    return dict(
        Place.objects.filter(**filters)
        .values("city_id")
        .annotate(total=Count("pk"))
        .values_list("city_id", "total")
    )


def _can_add_city(user):
    return (
        user.is_authenticated
        and (
            user.is_superuser
            or getattr(user, "role", None)
            in ("super_admin", "city_admin")
        )
    )


def _add_city_url():
    for name in (
        "dashboard:city_create",
        "dashboard:city_add",
        "admin:cities_city_add",
    ):
        try:
            return reverse(name)
        except NoReverseMatch:
            pass

    return ""


@login_required
def city_selection(request):
    selected_city = None
    selected_id = request.session.get("city_id")

    if selected_id:
        selected_city = (
            City.objects.select_related("province_ref")
            .filter(pk=selected_id)
            .first()
        )

    # Only cities with coordinates are sent here.
    # New PSGC rows have no invented coordinates.
    candidates = list(
        City.objects.filter(
            province_ref__isnull=False,
            latitude__isnull=False,
            longitude__isnull=False,
            status="active",
        ).select_related("province_ref")
        .values(
            "id",
            "name",
            "latitude",
            "longitude",
            "province_ref__slug",
            "province_ref__name",
        )
    )

    geo_cities = [
        {
            "id": c["id"],
            "name": c["name"],
            "latitude": float(c["latitude"]),
            "longitude": float(c["longitude"]),
            "province_slug": c["province_ref__slug"],
            "province_name": c["province_ref__name"],
        }
        for c in candidates
    ]

    context = {
        "selected_city": selected_city,
        "geo_cities": geo_cities,
        "can_add_city": _can_add_city(request.user),
        "add_city_url": (
            _add_city_url()
            if _can_add_city(request.user) else ""
        ),
    }

    return render(
        request,
        "cities/city_selection.html",
        context,
    )


@require_GET
@login_required
def api_provinces(request):
    provinces = Province.objects.order_by(
        "region", "name"
    ).values(
        "name", "slug", "region", "psgc_code"
    )

    return JsonResponse({
        "provinces": list(provinces)
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

    province = get_object_or_404(
        Province,
        slug=slug
    )

    queryset = City.objects.filter(
        province_ref=province
    )

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
    raw_id = request.POST.get(
        "city_id", ""
    ).strip()

    if not raw_id.isdigit():
        messages.error(
            request,
            "Choose an active city first."
        )
        return redirect("city_selection")

    city = get_object_or_404(
    City.objects.select_related("province_ref"),
    pk=int(raw_id),
    province_ref__isnull=False,
)
    request.session["city_id"] = city.pk
    request.session["selected_city_id"] = city.pk
    request.session["selected_city_name"] = city.name
    request.session["selected_province"] = (
        city.province_ref.name
    )

    request.session.pop("selected_hobbies", None)
    request.session.pop("hobbies_city_id", None)
    request.session.pop("attraction_search_query", None)

    messages.success(
        request,
        f"Welcome to {city.name}! Explore attractions in this city."
    )

    return redirect("places:city_discover")


