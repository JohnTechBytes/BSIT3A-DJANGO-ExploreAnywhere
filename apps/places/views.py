
import re

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.shortcuts import redirect, render

from apps.cities.models import City
from .models import Place, SavedPlace, Review
from .sample_images import sample_image_for


# Guard rail only: the carousel is designed to show every published place.
MAX_CAROUSEL_PLACES = 500

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

    # Phase 6F: one Discover Kabankalan URL with Browse / Nearby / Map modes.
    # Nearby reuses the existing verified-only queryset and browser-only GPS.
    # The previous /places/nearby/ URL is retained as a compatibility redirect.
    if (request.GET.get("mode") == "nearby" or
            any(key in request.GET for key in ("service", "place", "origin"))):
        from .nearby import nearby_places
        return nearby_places(request, unified=True)

    # The visitor must finish Hobby Selection first.
    # exploreanywhere-phase4f-direct-place-browse-v1
    # Browse published Kabankalan places without requiring a hobby session.

    # exploreanywhere-phase5a-discovery-controls-v1
    # Browse all resets the previous search; hobby personalization is preserved.
    browse_all = request.GET.get("browse") == "all"
    if browse_all:
        request.session.pop("attraction_search_query", None)
        search_query = ""
    elif "q" in request.GET:
        # Inline search shares the existing hobby-search session convention.
        search_query = (request.GET.get("q") or "").strip()[:200]
        if search_query:
            request.session["attraction_search_query"] = search_query
        else:
            request.session.pop("attraction_search_query", None)
    else:
        search_query = (
            request.session.get("attraction_search_query") or ""
        ).strip()[:200]

    # Phase 6A: natural-language service requests open nearby results directly.
    # Avoid changing hobby search sessions or normal attraction queries.
    if "q" in request.GET and search_query:
        from urllib.parse import urlencode as ea6_urlencode
        from django.urls import reverse as ea6_reverse
        from .nearby_intent import detect_service_intent
        if detect_service_intent(search_query):
            return redirect(
                ea6_reverse("places:attraction_carousel") + "?" +
                ea6_urlencode({"mode": "nearby", "q": search_query})
            )

    # Only offer category/hobby filters used by published Kabankalan places.
    published_places = (
        Place.objects.filter(city=city, is_active=True, is_verified=True)
        .select_related("city", "category")
    )
    available_categories = {}
    available_hobbies = {}
    published_total = 0
    for published_place in published_places.prefetch_related("hobbies"):
        published_total += 1
        if published_place.category_id and published_place.category:
            available_categories[str(published_place.category_id)] = str(published_place.category)
        for hobby in published_place.hobbies.all():
            if hobby.slug:
                available_hobbies[hobby.slug] = str(hobby)

    category_options = sorted(
        ({"value": key, "label": value} for key, value in available_categories.items()),
        key=lambda item: item["label"].casefold(),
    )
    hobby_options = sorted(
        ({"value": key, "label": value} for key, value in available_hobbies.items()),
        key=lambda item: item["label"].casefold(),
    )

    selected_category = "" if browse_all else (request.GET.get("category") or "").strip()
    selected_hobby = "" if browse_all else (request.GET.get("hobby") or "").strip()
    selected_sort = "recommended" if browse_all else (request.GET.get("sort") or "recommended")
    if selected_category not in available_categories:
        selected_category = ""
    if selected_hobby not in available_hobbies:
        selected_hobby = ""
    if selected_sort not in {"recommended", "rating", "name"}:
        selected_sort = "recommended"

    attractions = published_places
    if selected_category:
        attractions = attractions.filter(category_id=int(selected_category))
    if selected_hobby:
        attractions = attractions.filter(hobbies__slug=selected_hobby).distinct()

    # Apply the user's NLP search request.
    if search_query:
        search_filter = build_attraction_filter(search_query)

        if search_filter is not None:
            attractions = attractions.filter(search_filter)

    from .recommendations import rank_kabankalan_places

    # exploreanywhere-phase6i-inline-hobby-relevance
    # Use the Explore Places hobby dropdown without requiring a separate step.
    # If no filter is chosen, retain any previously saved preferences.
    scoring_hobbies = (
        [selected_hobby] if selected_hobby
        else request.session.get("selected_hobbies", [])
    )
    attractions = rank_kabankalan_places(
        attractions.prefetch_related("hobbies"),
        scoring_hobbies,
    )

    # Sorting affects display only; preserve existing recommendation scores.
    if selected_sort == "name":
        attractions.sort(key=lambda place: (place.title or "").casefold())
    elif selected_sort == "rating":
        attractions.sort(key=lambda place: (
            -float(place.avg_rating or 0),
            -int(place.review_count or 0),
            (place.title or "").casefold(),
        ))

    # The looping carousel shows every matching destination, so no pagination
    # page is sliced here. A high cap only guards against pathological datasets.
    total_matches = len(attractions)
    carousel_places = attractions[:MAX_CAROUSEL_PLACES]
    # Real photos remain authoritative; illustrative samples fill genuine gaps.
    for place in carousel_places:
        place.sample_image = sample_image_for(place) if not (place.cover_image or place.cover_image_url) else ""

    # exploreanywhere-phase5a2-discovery-clarity-v1
    # Remove-one controls retain the other active filters and clear q from the
    # existing search session when the Search chip is removed.
    from urllib.parse import urlencode

    active_state = {
        "q": search_query,
        "category": selected_category,
        "hobby": selected_hobby,
        "sort": selected_sort,
    }
    active_filter_chips = []
    labels = (
        ("q", "Search", search_query),
        ("category", "Category", available_categories.get(selected_category, "")),
        ("hobby", "Hobby", available_hobbies.get(selected_hobby, "")),
        (
            "sort", "Sort",
            {"name": "Name A–Z", "rating": "Highest rated"}.get(selected_sort, ""),
        ),
    )
    for field, label, value in labels:
        if not value:
            continue
        remaining_state = dict(active_state)
        remaining_state[field] = "recommended" if field == "sort" else ""
        active_filter_chips.append({
            "label": f"{label}: {value}",
            "remove_url": "?" + urlencode(remaining_state),
        })

    return render(
        request,
        "places/attraction_carousel.html",
        {
            "selected_city": city,
            "attractions": carousel_places,
            "total_attractions": total_matches,
            "carousel_truncated": total_matches > len(carousel_places),
            "selected_hobbies": scoring_hobbies,
            "search_query": search_query,
            "published_total": published_total,
            "category_options": category_options,
            "hobby_options": hobby_options,
            "selected_category": selected_category,
            "selected_hobby": selected_hobby,
            "selected_sort": selected_sort,
            "active_filter_chips": active_filter_chips,
            "active_discovery_mode": (
                "map" if request.GET.get("display") == "map" else "browse"
            ),
        },
    )

@login_required
def place_detail(request, pk):
    
    city = City.objects.get(
        pk=2,
        name__iexact="Kabankalan",
        province__iexact="Negros Occidental",
    )


    # phase4f: place details accessible without hobby-selection session
    # Saved Places, reviews and visit history must open details directly.

    from django.shortcuts import get_object_or_404

    place = get_object_or_404(
        Place.objects.select_related(
            "city", "category"
        ).prefetch_related(
            "photos", "opening_hours", "hobbies"
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

    place.sample_image = sample_image_for(place) if not (place.cover_image or place.cover_image_url) else ""

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
