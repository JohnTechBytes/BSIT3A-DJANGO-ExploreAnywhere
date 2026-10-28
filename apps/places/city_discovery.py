from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from .models import Place


def city_discover(request):
    city_id = (
        request.session.get("selected_city_id")
        or request.session.get("city_id")
    )

    if not city_id:
        return redirect("/cities/select/")

    places = (
        Place.objects
        .filter(city_id=city_id)
        .select_related("city", "category")
        .order_by("-is_verified", "-is_active", "title")
    )

    paginator = Paginator(places, 24)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "places/city_discover.html",
        {
            "page_obj": page_obj,
            "city_name": request.session.get(
                "selected_city_name", "Selected City"
            ),
            "total_places": paginator.count,
        },
    )
