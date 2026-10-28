import re

from django.db.models import Case, IntegerField, Q, Value, When
from django.shortcuts import render

from apps.cities.locking import LOCKED_CITY_PK
from apps.core.models import Category
from apps.places.models import Place
from apps.places.sample_images import sample_image_for


def home(request):
    """Feature published local records, prioritizing the existing OSM imports."""
    published = Place.objects.filter(
        city_id=LOCKED_CITY_PK, is_active=True, is_verified=True,
    )
    categories = Category.objects.filter(places__in=published).distinct().order_by("name")
    selected_category = request.GET.get("category", "")
    places = published
    if selected_category:
        places = places.filter(category__slug=selected_category)
    places = places.annotate(
        osm_priority=Case(
            When(slug__startswith="osm-", then=Value(1)),
            default=Value(0), output_field=IntegerField(),
        ),
        photo_priority=Case(
            When(
                (Q(cover_image__isnull=False) & ~Q(cover_image=""))
                | (Q(cover_image_url__isnull=False) & ~Q(cover_image_url="")),
                then=Value(1),
            ),
            default=Value(0), output_field=IntegerField(),
        ),
    ).select_related("category").prefetch_related("hobbies").order_by(
        "-osm_priority", "-photo_priority", "-avg_rating", "-review_count", "title", "pk",
    )
    featured_places = list(places[:9])
    for place in featured_places:
        place.sample_image = sample_image_for(place) if not (place.cover_image or place.cover_image_url) else ""
        # The importer's osm-type-id slug is the existing provenance identifier.
        match = re.fullmatch(r"osm-(node|way|relation)-(\d+)", place.slug)
        place.osm_source_url = (
            f"https://www.openstreetmap.org/{match[1]}/{match[2]}" if match else ""
        )
    # Prefer a real photo for the hero even when the first OSM record has none.
    hero_place = next(
        (place for place in featured_places if place.cover_image or place.cover_image_url),
        featured_places[0] if featured_places else None,
    )
    return render(request, "home.html", {
        "featured_places": featured_places,
        "hero_place": hero_place,
        "categories": categories,
        "selected_category": selected_category,
        "published_count": published.count(),
        "osm_count": published.filter(slug__startswith="osm-").count(),
    })


def error_404(request, exception=None):
    """Dark editorial 404 page; used when DEBUG is off."""
    return render(request, "errors/404.html", status=404)


def error_500(request):
    """Dark editorial 500 page; used when DEBUG is off."""
    return render(request, "errors/500.html", status=500)
