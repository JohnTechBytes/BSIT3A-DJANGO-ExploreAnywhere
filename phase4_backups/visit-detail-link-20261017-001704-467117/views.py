
import re

from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.cities.models import City
from .models import Place, SavedPlace, Review


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
    """Match named Kabankalan places precisely; expand only broad category searches.

    The caller already limits records to verified, published Kabankalan places.
    Query-based filtering is separate from hobby/rating recommendation ranking.
    """
    # ExploreAnywhere Phase 4E named-destination search fix v1
    import unicodedata

    normalized = unicodedata.normalize(
        "NFKD", str(search_text or "")[:300]
    ).encode("ascii", "ignore").decode("ascii").lower()
    words = re.findall(r"[a-z0-9]+", normalized)
    if not words:
        return None

    # City/province words are location qualifiers, not attraction keywords.
    # The view itself already enforces Kabankalan via city_id=2.
    location_words = {
        "kabankalan", "city", "negros", "occidental", "philippines",
    }
    filler_words = STOP_WORDS | {
        "attraction", "attractions", "destination", "destinations",
        "thing", "things", "do", "around", "within", "nearby",
        "spot", "spots", "tourist", "site", "sites", "best", "top",
        "looking", "from", "my", "and", "hopping", "activity", "activities",
    }
    keywords = list(dict.fromkeys(
        word for word in words
        if word not in location_words
        and word not in filler_words
        and len(word) >= 2
    ))

    # "places in Kabankalan" is a browse-all request, not a failed search.
    if not keywords:
        return None

    matched_intents = [
        name for name, intent in SEARCH_INTENTS.items()
        if any(word in intent["triggers"] for word in keywords)
    ]
    generic_words = {
        word
        for intent in SEARCH_INTENTS.values()
        for word in intent["triggers"] + intent["terms"]
    } | {
        "mount", "mountain", "mountains", "hill", "hills", "peak", "peaks",
        "plaza", "museum", "park", "parks", "trail", "trails", "river",
        "food", "photography", "gaming", "art", "culture", "shopping",
        "billiards", "basketball", "music", "swimming",
    }

    # A distinctive name token (Amyan, CPSU, Mag, Aso, Nai-guin, etc.) means
    # the visitor is looking for a particular place, not all places of a type.
    # Require every name token to appear in the title, preventing broad OR
    # matches from yielding nearly all places for "CPSU Museum".
    distinctive_words = [w for w in keywords if w not in generic_words]
    if distinctive_words:
        ignored_modifiers = {
            "nature", "hiking", "photography", "swimming", "beach",
            "beaches", "food", "eat", "cafe", "coffee", "shopping",
            "gaming", "music", "art", "culture",
        }
        name_words = [w for w in keywords if w not in ignored_modifiers]
        name_filter = Q()
        for word in name_words:
            name_filter &= Q(title__icontains=word)
        return name_filter

    # "Kabankalan Plaza" or "plaza in Kabankalan" should only find
    # the actual place title, not unrelated places mentioning Kabankalan.
    if "kabankalan" in words and not matched_intents:
        title_filter = Q()
        for word in keywords:
            title_filter &= Q(title__icontains=word)
        return title_filter

    # Broad searches such as "nature", "museum" and "waterfalls" can use
    # known types and matching text. Do not demand the correct category slug
    # alone, because some verified records still have a generic category.
    if matched_intents:
        category_slugs = {
            "beach": ("beach",),
            "waterfall": ("waterfall",),
            "history": (
                "museum", "memorial", "monument", "historic-ruins",
                "historic-fort", "archaeological-site",
            ),
        }
        terms = set()
        slugs = set()
        for name in matched_intents:
            terms.update(SEARCH_INTENTS[name]["terms"])
            slugs.update(category_slugs.get(name, ()))

        broad_filter = Q()
        if slugs:
            broad_filter |= Q(category__slug__in=sorted(slugs))
        for term in sorted(terms):
            broad_filter |= Q(title__icontains=term)
            broad_filter |= Q(description__icontains=term)
            broad_filter |= Q(address__icontains=term)
            broad_filter |= Q(category__name__icontains=term)
        return broad_filter

    # Plain terms such as "plaza" require a match to the supplied terms.
    # AND across words prevents location text from matching every destination.
    text_filter = Q()
    for word in keywords:
        text_filter &= (
            Q(title__icontains=word)
            | Q(description__icontains=word)
            | Q(address__icontains=word)
            | Q(barangay__icontains=word)
            | Q(category__name__icontains=word)
        )
    return text_filter

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
            "is_saved": SavedPlace.objects.filter(user=request.user, place=place).exists(),
            # ExploreAnywhere phase3e reviews v1
            "my_review": Review.objects.filter(user=request.user, place=place).order_by("pk").first(),
            "public_reviews": Review.objects.filter(place=place).select_related("user").order_by("-created_at")[:8],
            "review_rating_options": (5, 4, 3, 2, 1),
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

# ExploreAnywhere phase3 save-and-journey v1
