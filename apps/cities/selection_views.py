from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_POST

from .models import City


@login_required
def select_city(request):
    cities = list(
        City.objects.filter(
            status=City.Status.ACTIVE
        ).order_by("province", "name")
    )

    province_groups = [
        {
            "province": province,
            "cities": list(group)
        }
        for province, group in groupby(
            cities,
            key=lambda city: city.province
        )
    ]

    return render(
        request,
        "cities/select_city.html",
        {
            "province_groups": province_groups,
            "province_total": len(province_groups),
            "city_total": len(cities),
            "selected_id": request.session.get(
                "selected_city_id"
            ),
        }
    )


@login_required
@require_POST
def choose_city(request):
    city_id = request.POST.get("city_id", "").strip()

    if not city_id.isdigit():
        messages.error(
            request,
            "Please select a city first."
        )
        return redirect("city_selection")

    city = get_object_or_404(
        City,
        pk=int(city_id),
        status=City.Status.ACTIVE
    )

    request.session["selected_city_id"] = city.pk
    request.session["selected_city_name"] = city.name
    request.session["selected_province"] = city.province

    for route in (
        "hobby_selection",
        "hobbies:select",
        "select_hobbies",
    ):
        try:
            return redirect(reverse(route))
        except NoReverseMatch:
            pass

    messages.success(
        request,
        f"{city.name}, {city.province} selected successfully."
    )

    return redirect("city_selection")
