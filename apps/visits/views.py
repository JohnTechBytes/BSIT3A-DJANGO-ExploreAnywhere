"""Kabankalan-only, authenticated check-ins with manual staff review."""
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_GET, require_http_methods

from apps.places.models import Place
from .models import VisitCheckIn
from .services import visit_rewards

CITY_ID = 2
MIN_NOTE_LENGTH = 20
MAX_NOTE_LENGTH = 1000


def _published():
    return Place.objects.filter(city_id=CITY_ID, is_active=True, is_verified=True)


@login_required
@require_http_methods(['GET', 'POST'])
def check_in(request, pk):
    place = get_object_or_404(_published(), pk=pk)
    previous = VisitCheckIn.objects.filter(user=request.user, place=place).first()
    today = timezone.localdate()

    if request.method == 'POST':
        note = (request.POST.get('visit_note') or '').strip()
        visit_date_raw = (request.POST.get('visited_on') or '').strip()
        try:
            visit_date = date.fromisoformat(visit_date_raw)
        except (ValueError, TypeError):
            messages.error(request, 'Enter a valid visit date.')
            return redirect('visits:check_in', pk=pk)
        if visit_date > today or visit_date < date(2020, 1, 1):
            messages.error(request, 'The visit date must be between 2020 and today.')
            return redirect('visits:check_in', pk=pk)
        if not MIN_NOTE_LENGTH <= len(note) <= MAX_NOTE_LENGTH:
            messages.error(request, 'Provide a 20–1,000 character visit note for review.')
            return redirect('visits:check_in', pk=pk)

        # One submitted visit per user and destination; resubmit only if rejected.
        with transaction.atomic():
            checkin, created = VisitCheckIn.objects.select_for_update().get_or_create(
                user=request.user,
                place=place,
                defaults={"visited_on": visit_date, "visit_note": note},
            )
            if created:
                messages.success(request, 'Check-in submitted for staff review. No points awarded yet.')
            elif checkin.status == VisitCheckIn.Status.REJECTED:
                checkin.visited_on = visit_date
                checkin.visit_note = note
                checkin.status = VisitCheckIn.Status.PENDING
                checkin.reviewed_at = None
                checkin.reviewed_by = None
                checkin.reviewer_note = ''
                checkin.save(update_fields=[
                    'visited_on', 'visit_note', 'status', 'reviewed_at',
                    'reviewed_by', 'reviewer_note',
                ])
                messages.success(request, 'Your corrected check-in was submitted for review.')
            else:
                messages.info(request, 'This destination already has a pending or approved check-in.')
        return redirect('visits:list')

    return render(request, 'visits/check_in.html', {
        'place': place, 'checkin': previous, 'today': today,
    })


@login_required
@require_GET
def my_visits(request):
    entries = (VisitCheckIn.objects
        .filter(user=request.user, place__city_id=CITY_ID)
        .select_related('place').order_by('-submitted_at'))
    approved_count = entries.filter(status=VisitCheckIn.Status.APPROVED).count()
    pending_count = entries.filter(status=VisitCheckIn.Status.PENDING).count()
    rewards = visit_rewards(approved_count)
    return render(request, 'visits/my_visits.html', {
        'entries': entries, 'approved_count': approved_count,
        'pending_count': pending_count, 'reward_points': rewards['points'],
        'badges': rewards['badges'],
    })
