from django.shortcuts import render

from apps.cities.locking import LOCKED_CITY_PK
from apps.core.models import Category
from apps.places.models import Place


def home(request):
    """Show real, published Kabankalan content on the public landing page."""
    places = Place.objects.filter(
        city_id=LOCKED_CITY_PK, is_active=True, is_verified=True,
    ).select_related("category").prefetch_related("hobbies")
    categories = Category.objects.filter(places__in=places).distinct().order_by("name")
    selected_category = request.GET.get("category", "")
    if selected_category:
        places = places.filter(category__slug=selected_category)
    featured_places = list(places.order_by("-avg_rating", "-review_count", "title")[:6])
    return render(request, "home.html", {
        "featured_places": featured_places,
        "hero_place": featured_places[0] if featured_places else None,
        "categories": categories,
        "selected_category": selected_category,
    })
