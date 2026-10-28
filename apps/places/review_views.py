"""ExploreAnywhere Phase 3E: user-owned Kabankalan reviews."""
from decimal import Decimal, ROUND_HALF_UP

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Avg, Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Place, Review

CITY_ID = 2
MAX_COMMENT_LENGTH = 1500


def _published():
    return Place.objects.filter(city_id=CITY_ID, is_active=True, is_verified=True)


def _sync_rating(place):
    # Call only inside the transaction while holding the Place row lock.
    aggregate = Review.objects.filter(place=place).aggregate(
        total=Count('pk'), mean=Avg('rating'))
    mean = aggregate['mean']
    place.review_count = aggregate['total'] or 0
    place.avg_rating = (Decimal(str(mean)).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP) if mean is not None
        else Decimal('0.00'))
    place.save(update_fields=['review_count', 'avg_rating'])


@login_required
@require_POST
def submit_review(request, pk):
    # Reject tampered ratings and oversized comments, without changing records.
    rating_text = (request.POST.get('rating') or '').strip()
    comment = (request.POST.get('comment') or '').strip()
    if rating_text not in {'1', '2', '3', '4', '5'}:
        messages.error(request, 'Choose a rating from 1 to 5 stars.')
        return redirect('places:place_detail', pk=pk)
    if len(comment) > MAX_COMMENT_LENGTH:
        messages.error(request, 'Review comment must be at most 1,500 characters.')
        return redirect('places:place_detail', pk=pk)

    # Lock place row to serialize our review mutations for this destination.
    with transaction.atomic():
        place = get_object_or_404(_published().select_for_update(), pk=pk)
        review = (Review.objects.filter(user=request.user, place=place)
                  .order_by('pk').first())
        if review is None:
            Review.objects.create(user=request.user, place=place,
                                  rating=int(rating_text), comment=comment)
            messages.success(request, 'Your review was submitted.')
        else:
            review.rating = int(rating_text)
            review.comment = comment
            review.save(update_fields=['rating', 'comment'])
            messages.success(request, 'Your review was updated.')
        _sync_rating(place)
    return redirect('places:place_detail', pk=pk)


@login_required
@require_POST
def delete_review(request, pk):
    with transaction.atomic():
        place = get_object_or_404(Place.objects.filter(city_id=CITY_ID)
                                  .select_for_update(), pk=pk)
        deleted, _ = Review.objects.filter(user=request.user, place=place).delete()
        if deleted:
            _sync_rating(place)
            messages.success(request, 'Your review was deleted.')
    if place.is_active and place.is_verified:
        return redirect('places:place_detail', pk=pk)
    return redirect('places:my_reviews')


@login_required
def my_reviews(request):
    reviews = (Review.objects.filter(user=request.user, place__city_id=CITY_ID)
               .select_related('place', 'place__category').order_by('-created_at'))
    return render(request, 'places/my_reviews.html', {'reviews': reviews})
