"""ExploreAnywhere phase3 save-and-journey v1.

All public place collections are restricted to verified, active Kabankalan places.
Saving and unsaving use POST + CSRF, with data scoped to the current user.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Place, Review, SavedPlace
from .sample_images import sample_image_for

KABANKALAN_CITY_ID = 2


def _public_places():
    return Place.objects.filter(
        city_id=KABANKALAN_CITY_ID,
        is_verified=True,
        is_active=True,
    )


@login_required
@require_POST
def save_place(request, pk):
    place = get_object_or_404(_public_places(), pk=pk)
    SavedPlace.objects.get_or_create(user=request.user, place=place)
    return redirect("places:place_detail", pk=place.pk)


@login_required
@require_POST
def unsave_place(request, pk):
    # Allow removing a saved Kabankalan place even if it was unpublished later.
    place = get_object_or_404(Place, pk=pk, city_id=KABANKALAN_CITY_ID)
    SavedPlace.objects.filter(user=request.user, place=place).delete()
    return redirect("places:place_detail", pk=pk) if (
        place.is_active and place.is_verified
    ) else redirect("places:saved_places")


@login_required
def saved_places(request):
    entries = (SavedPlace.objects
        .filter(user=request.user, place__city_id=KABANKALAN_CITY_ID,
                place__is_active=True, place__is_verified=True)
        .select_related("place", "place__category", "place__city")
        .order_by("-created_at"))
    entries = list(entries)
    for entry in entries:
        place = entry.place
        place.sample_image = (sample_image_for(place)
                              if not (place.cover_image or place.cover_image_url) else "")
    return render(request, "places/saved_places.html", {
        "entries": entries,
    })


@login_required
def journey_dashboard(request):
    from apps.itineraries.models import Itinerary

    saved = (SavedPlace.objects
        .filter(user=request.user, place__city_id=KABANKALAN_CITY_ID,
                place__is_active=True, place__is_verified=True)
        .select_related("place")
        .order_by("-created_at"))
    itineraries = (Itinerary.objects
        .filter(user=request.user, city_id=KABANKALAN_CITY_ID)
        .order_by("-updated_at"))
    review_count = Review.objects.filter(
        user=request.user, place__city_id=KABANKALAN_CITY_ID,
    ).count()
    # ExploreAnywhere phase3f visits-and-rewards v1
    from apps.visits.models import VisitCheckIn
    from apps.visits.services import visit_rewards
    my_checkins = (VisitCheckIn.objects.filter(user=request.user, place__city_id=2)
                   .select_related("place").order_by("-submitted_at"))
    approved_visit_count = my_checkins.filter(status=VisitCheckIn.Status.APPROVED).count()
    pending_visit_count = my_checkins.filter(status=VisitCheckIn.Status.PENDING).count()
    visit_rewards_data = visit_rewards(approved_visit_count)

    # The visitor's own interests and search history.
    from apps.core.models import Hobby
    from apps.info.models import QueryLog, RecommendationRating

    hobby_slugs = [
        slug for slug in (request.session.get("selected_hobbies") or []) if slug
    ]
    hobby_names = {
        hobby.slug: hobby.name
        for hobby in Hobby.objects.filter(slug__in=hobby_slugs)
    }
    interest_rows = [
        {"slug": slug, "name": hobby_names.get(slug, slug.replace("-", " ").title())}
        for slug in hobby_slugs
    ]
    recent_searches = list(
        QueryLog.objects.filter(user=request.user).order_by("-created_at", "-pk")[:5]
    )
    relevance_ratings = list(
        RecommendationRating.objects.filter(user=request.user)
        .select_related("place")
        .order_by("-created_at", "-pk")[:5]
    )
    return render(request, "places/journey_dashboard.html", {
        "saved_count": saved.count(),
        "saved_preview": saved[:4],
        "itinerary_count": itineraries.count(),
        "itinerary_preview": itineraries[:4],
        "review_count": review_count,
        "approved_visit_count": approved_visit_count,
        "pending_visit_count": pending_visit_count,
        "visit_points": visit_rewards_data["points"],
        "visit_badges": visit_rewards_data["badges"],
        "visits_preview": my_checkins[:3],
        "my_reviews_preview": (Review.objects.filter(user=request.user, place__city_id=KABANKALAN_CITY_ID)
            .select_related("place").order_by("-created_at")[:4]),  # ExploreAnywhere phase3e reviews v1
        # Interests, search history and relevance feedback (P2)
        "interest_rows": interest_rows,
        "recent_searches": recent_searches,
        "relevance_ratings": relevance_ratings,
    })
