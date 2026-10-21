
import re

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.cities.models import City
from .models import Place


# Search intent -> possible words in attraction records.
SEARCH_INTENTS = {
    "beach": {
        "triggers": ["beach", "beaches", "swimming", "seaside"],
        "terms": ["beach", "coast", "seaside", "shore", "bay"],
    },
    "waterfall": {
        "triggers": ["waterfall", "waterfalls", "falls"],
        "terms": ["waterfall", "falls", "cascade"],
    },
    "nature": {
        "triggers": ["nature", "forest", "mountain", "hiking"],
        "terms": [
            "forest", "mountain", "trail", "hiking",
            "nature", "park", "hill", "peak",
        ],
    },
    "history": {
        "triggers": ["history", "historical", "heritage", "museum"],
        "terms": [
            "museum", "heritage", "historical",
            "monument", "memorial", "shrine",
        ],
    },
    "food": {
        "triggers": ["food", "eat", "restaurant", "cafe", "coffee"],
        "terms": [
            "restaurant", "cafe", "coffee",
            "eatery", "food", "dining",
        ],
    },
}

STOP_WORDS = {
    "i", "want", "to", "go", "a", "an", "the",
    "in", "at", "of", "for", "me", "find",
    "show", "places", "place", "visit", "near",
    "some", "where", "can", "you", "please",
    "would", "like", "explore",
}


def build_attraction_filter(search_text):
    """
    Return a database Q filter from simple search intent.

    Uses attraction titles, descriptions and addresses.
    Does not invent a category or use external AI.
    """
    words = re.findall(r"[a-z]+", search_text.lower())

    if not words:
        return None

    terms = []

    for intent in SEARCH_INTENTS.values():
        if any(trigger in words for trigger in intent["triggers"]):
            terms.extend(intent["terms"])

    if not terms:
        terms = [
            word for word in words
            if word not in STOP_WORDS and len(word) >= 3
        ]

    # Do not return unrelated places when no useful term exists.
    if not terms:
        return Q(pk__in=[])

   
    filters = Q()

    # Strong intent matching:
    # For supported specific destination types, use exact
    # category classification where possible.
    exact_categories = {
        "beach": ["beach"],
        "waterfall": ["waterfall"],
        "history": [
            "museum",
            "memorial",
            "monument",
            "historic-ruins",
            "historic-fort",
            "archaeological-site",
        ],
    }

    matched_intents = [
        name
        for name, config in SEARCH_INTENTS.items()
        if any(
            trigger in words
            for trigger in config["triggers"]
        )
    ]

    category_slugs = []

    for intent in matched_intents:
        category_slugs.extend(
            exact_categories.get(intent, [])
        )

    if category_slugs:
        return Q(
            category__slug__in=set(category_slugs)
        )

    # Fallback search for requests that do not have a
    # supported exact category mapping.
    for term in set(terms):
        filters |= Q(title__icontains=term)
        filters |= Q(description__icontains=term)
        filters |= Q(address__icontains=term)
        filters |= Q(category__name__icontains=term)

    return filters



@login_required
def attraction_carousel(request):
   
    # ExploreAnywhere: Kabankalan City Edition
    city_id = 2

    # Keep existing session-dependent templates compatible.
    request.session["city_id"] = city_id
    request.session["selected_city_id"] = city_id
    request.session["selected_city_name"] = "Kabankalan"
    request.session["selected_province"] = "Negros Occidental"

    if not city_id:
        return redirect("city_selection")

    city = City.objects.filter(pk=city_id).first()

    if city is None:
        return redirect("city_selection")

    # The visitor must finish Hobby Selection first.
    if (
        request.session.get("hobbies_city_id") != city.pk
        or not request.session.get("selected_hobbies")
    ):
        return redirect("hobbies:select")

    search_query = (
        request.session.get("attraction_search_query") or ""
    ).strip()

    attractions = (
        Place.objects.filter(
            city=city,
            is_active=True,
            is_verified=True,
        )
        .select_related("city", "category")
    )

    # Apply the user's NLP search request.
    if search_query:
        search_filter = build_attraction_filter(search_query)

        if search_filter is not None:
            attractions = attractions.filter(search_filter)

    from .recommendations import rank_kabankalan_places

    attractions = rank_kabankalan_places(
        attractions.prefetch_related("hobbies"),
        request.session.get("selected_hobbies", []),
    )

    paginator = Paginator(attractions, 12)
    page = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "places/attraction_carousel.html",
        {
            "selected_city": city,
            "attractions": page,
            "page_obj": page,
            "total_attractions": paginator.count,
            "selected_hobbies": request.session.get(
                "selected_hobbies", []
            ),
            "search_query": search_query,
        },
    )

@login_required
def place_detail(request, pk):
    
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

    from django.shortcuts import get_object_or_404

    place = get_object_or_404(
        Place.objects.select_related(
            "city", "category"
        ).prefetch_related(
            "photos", "opening_hours"
        ),
        pk=pk,
        city=city,
        is_active=True,
        is_verified=True,
    )

    photos = [
        photo for photo in place.photos.all()
        if photo.image or photo.image_url
    ]

    nearby_places = (
        Place.objects.filter(
            city=city,
            is_active=True,
            is_verified=True,
        )
        .exclude(pk=place.pk)
        .select_related("category")
        .order_by("-avg_rating", "title")[:4]
    )

    return render(
        request,
        "places/place_detail.html",
        {
            "place": place,
            "photos": photos,
            "nearby_places": nearby_places,
            "opening_hours": place.opening_hours.all(),
            "selected_city": city,
        },
    )


from django.core.paginator import Paginator
from django.shortcuts import redirect, render
from .models import Place



def city_discover(request):
    city_id = 2

    places = (
        Place.objects
        .filter(city_id=city_id)
        .select_related("city", "category")
        .order_by("-is_verified", "-is_active", "title")
    )


    paginator = Paginator(places, 24)
    page_obj = paginator.get_page(
        request.GET.get("page")
    )

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
