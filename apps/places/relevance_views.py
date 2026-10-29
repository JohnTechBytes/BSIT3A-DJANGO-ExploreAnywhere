"""Record how relevant a recommended destination was.

The rating answers one question: for the search that produced this result,
was the destination relevant? The answer is stored per visitor, per search
and per destination, so the staff dashboard can compare what the system
recommended with what the visitor actually found useful.
"""
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect
from django.views.decorators.http import require_POST

from apps.cities.locking import LOCKED_CITY_PK
from apps.info.models import RecommendationRating

from .models import Place

RATING_LABELS = dict(RecommendationRating.RatingChoices.choices)


@login_required
@require_POST
def rate_relevance(request, pk):
    """Store the visitor's relevance rating for one recommended place."""
    place = get_object_or_404(
        Place,
        pk=pk,
        city_id=LOCKED_CITY_PK,
        is_active=True,
        is_verified=True,
    )

    rating = (request.POST.get("rating") or "").strip()
    if rating not in RATING_LABELS:
        messages.error(request, "Please choose how relevant this result was.")
        return redirect("places:place_detail", pk=place.pk)

    # The rating belongs to the search that produced the result. The visitor
    # can override it, but the active search is the default.
    query_text = (
        request.POST.get("query_text")
        or request.session.get("attraction_search_query")
        or ""
    ).strip()[:255]

    RecommendationRating.objects.update_or_create(
        user=request.user,
        place=place,
        query_text=query_text,
        defaults={"rating": rating},
    )

    messages.success(
        request,
        "Thanks — this recommendation is marked as %s."
        % RATING_LABELS[rating].lower(),
    )
    return redirect("places:place_detail", pk=place.pk)
