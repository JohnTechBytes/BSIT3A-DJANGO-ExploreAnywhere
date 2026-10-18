"""Kabankalan-only, user-owned itinerary planning (Phase 3D)."""
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods, require_POST

from apps.places.models import Place, SavedPlace
from .models import Itinerary, ItineraryStop

CITY_ID = 2


def _places():
    return Place.objects.filter(city_id=CITY_ID, is_verified=True, is_active=True)


def _trip(user, pk):
    return get_object_or_404(Itinerary, pk=pk, user=user, city_id=CITY_ID)


def _trip_title(value):
    value = (value or '').strip()
    if not (1 <= len(value) <= 255):
        raise ValueError('Enter a trip title of 1 to 255 characters.')
    return value


def _trip_day(value):
    try:
        day = int(value)
    except (TypeError, ValueError):
        raise ValueError('Enter a valid day number.')
    if not 1 <= day <= 365:
        raise ValueError('Day number must be between 1 and 365.')
    return day


def _stop_time(value):
    try:
        return datetime.strptime((value or '').strip(), '%H:%M').time()
    except ValueError:
        raise ValueError('Choose a valid time for this stop.')


def _saved_ids(user):
    return set(SavedPlace.objects.filter(
        user=user, place__city_id=CITY_ID, place__is_verified=True,
        place__is_active=True).values_list('place_id', flat=True))


@login_required
@require_http_methods(['GET'])
def my_itineraries(request):
    trips = (Itinerary.objects.filter(user=request.user, city_id=CITY_ID)
             .annotate(stop_count=Count('stops')).order_by('-updated_at'))
    return render(request, 'itineraries/my_itineraries.html', {'trips': trips})


@login_required
@require_http_methods(['GET', 'POST'])
def create_itinerary(request):
    selected = request.GET.get('place', '') if request.method == 'GET' else request.POST.get('initial_place', '')
    if request.method == 'POST':
        try:
            title = _trip_title(request.POST.get('title'))
            day = _trip_day(request.POST.get('day_number', '1'))
            place = None
            start_time = None
            if selected:
                if not str(selected).isdigit():
                    raise ValueError('Select an available Kabankalan destination.')
                place = _places().filter(pk=int(selected)).first()
                if not place:
                    raise ValueError('That destination is no longer available.')
                start_time = _stop_time(request.POST.get('start_time'))
            with transaction.atomic():
                trip = Itinerary.objects.create(user=request.user, city_id=CITY_ID,
                                                title=title, day_number=day)
                if place:
                    ItineraryStop.objects.create(itinerary=trip, place=place,
                                                 start_time=start_time, stop_order=1)
            messages.success(request, 'Your Kabankalan itinerary was created.')
            return redirect('itineraries:builder', pk=trip.pk)
        except ValueError as exc:
            messages.error(request, str(exc))
    choices = _places().order_by('title')
    return render(request, 'itineraries/create.html', {
        'places': choices, 'selected_place': str(selected),
        'saved_ids': _saved_ids(request.user),
        'input_title': request.POST.get('title', '') if request.method == 'POST' else '',
        'input_day': request.POST.get('day_number', '1') if request.method == 'POST' else '1',
        'input_time': request.POST.get('start_time', '09:00') if request.method == 'POST' else '09:00',
    })


@login_required
@require_http_methods(['GET'])
def builder(request, pk):
    trip = _trip(request.user, pk)
    stops = list(trip.stops.select_related('place').order_by('stop_order', 'pk'))
    return render(request, 'itineraries/builder.html', {
        'trip': trip, 'stops': stops, 'places': _places().order_by('title'),
        'saved_ids': _saved_ids(request.user),
    })


@login_required
@require_POST
def update_itinerary(request, pk):
    trip = _trip(request.user, pk)
    try:
        trip.title = _trip_title(request.POST.get('title'))
        trip.day_number = _trip_day(request.POST.get('day_number'))
        trip.save(update_fields=['title', 'day_number', 'updated_at'])
        messages.success(request, 'Trip details updated.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('itineraries:builder', pk=pk)


@login_required
@require_POST
def add_stop(request, pk):
    try:
        with transaction.atomic():
            trip = get_object_or_404(Itinerary.objects.select_for_update(),
                                     pk=pk, user=request.user, city_id=CITY_ID)
            raw_id = (request.POST.get('place_id') or '').strip()
            if not raw_id.isdigit():
                raise ValueError('Select a Kabankalan destination.')
            place = get_object_or_404(_places(), pk=int(raw_id))
            if ItineraryStop.objects.filter(itinerary=trip, place=place).exists():
                raise ValueError('That destination is already in your itinerary.')
            when = _stop_time(request.POST.get('start_time'))
            notes = (request.POST.get('notes') or '').strip()
            if len(notes) > 255:
                raise ValueError('Stop notes must be 255 characters or less.')
            last = (ItineraryStop.objects.filter(itinerary=trip)
                    .order_by('-stop_order').values_list('stop_order', flat=True).first() or 0)
            ItineraryStop.objects.create(itinerary=trip, place=place, start_time=when,
                                         stop_order=last + 1, notes=notes)
        messages.success(request, 'Destination added to your trip.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('itineraries:builder', pk=pk)


@login_required
@require_POST
def update_stop(request, pk, stop_id):
    trip = _trip(request.user, pk)
    stop = get_object_or_404(ItineraryStop, pk=stop_id, itinerary=trip)
    try:
        when = _stop_time(request.POST.get('start_time'))
        notes = (request.POST.get('notes') or '').strip()
        if len(notes) > 255:
            raise ValueError('Stop notes must be 255 characters or less.')
        stop.start_time = when
        stop.notes = notes
        stop.save(update_fields=['start_time', 'notes'])
        messages.success(request, 'Stop details updated.')
    except ValueError as exc:
        messages.error(request, str(exc))
    return redirect('itineraries:builder', pk=pk)


def _renumber(stops):
    for order, stop in enumerate(stops, 1):
        if stop.stop_order != order:
            ItineraryStop.objects.filter(pk=stop.pk).update(stop_order=order)


@login_required
@require_POST
def remove_stop(request, pk, stop_id):
    with transaction.atomic():
        trip = get_object_or_404(Itinerary.objects.select_for_update(),
                                 pk=pk, user=request.user, city_id=CITY_ID)
        stop = get_object_or_404(ItineraryStop, pk=stop_id, itinerary=trip)
        stop.delete()
        stops = list(ItineraryStop.objects.filter(itinerary=trip).order_by('stop_order', 'pk'))
        _renumber(stops)
    messages.success(request, 'Stop removed.')
    return redirect('itineraries:builder', pk=pk)


@login_required
@require_POST
def move_stop(request, pk, stop_id):
    direction = request.POST.get('direction')
    if direction not in ('up', 'down'):
        messages.error(request, 'Invalid reorder action.')
        return redirect('itineraries:builder', pk=pk)
    with transaction.atomic():
        trip = get_object_or_404(Itinerary.objects.select_for_update(),
                                 pk=pk, user=request.user, city_id=CITY_ID)
        stops = list(ItineraryStop.objects.filter(itinerary=trip).order_by('stop_order', 'pk'))
        indices = [i for i, stop in enumerate(stops) if stop.pk == stop_id]
        if not indices:
            from django.http import Http404
            raise Http404('Stop not found')
        i = indices[0]
        j = i - 1 if direction == 'up' else i + 1
        if 0 <= j < len(stops):
            stops[i], stops[j] = stops[j], stops[i]
            _renumber(stops)
            messages.success(request, 'Stop order updated.')
    return redirect('itineraries:builder', pk=pk)


@login_required
@require_POST
def delete_itinerary(request, pk):
    with transaction.atomic():
        trip = get_object_or_404(Itinerary.objects.select_for_update(),
                                 pk=pk, user=request.user, city_id=CITY_ID)
        trip.delete()
    messages.success(request, 'Itinerary deleted.')
    return redirect('itineraries:list')


# exploreanywhere-itinerary-chooser-v1
@login_required
@require_http_methods(['GET', 'POST'])
def choose_for_place(request, place_id):
    """Let an authenticated visitor add one Kabankalan place to an owned trip."""
    from django.db.models import Count, Exists, OuterRef

    place = get_object_or_404(_places(), pk=place_id)
    if request.method == 'POST':
        raw_trip_id = (request.POST.get('itinerary_id') or '').strip()
        if not (raw_trip_id.isdigit() and 1 <= len(raw_trip_id) <= 18):
            messages.error(request, 'Choose one of your itineraries first.')
            return redirect('itineraries:choose_for_place', place_id=place.pk)
        try:
            arrival = _stop_time(request.POST.get('start_time'))
            notes = (request.POST.get('notes') or '').strip()
            if len(notes) > 255:
                raise ValueError('Stop notes must be 255 characters or less.')
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect('itineraries:choose_for_place', place_id=place.pk)

        # The parent-trip lock serializes additions to this itinerary, preventing
        # duplicate stops even if the same form is submitted in parallel.
        with transaction.atomic():
            trip = get_object_or_404(
                Itinerary.objects.select_for_update(),
                pk=int(raw_trip_id), user=request.user, city_id=CITY_ID,
            )
            if ItineraryStop.objects.filter(itinerary=trip, place=place).exists():
                messages.info(request, 'This destination is already in that itinerary.')
            else:
                position = (ItineraryStop.objects.filter(itinerary=trip)
                            .order_by('-stop_order')
                            .values_list('stop_order', flat=True).first() or 0) + 1
                ItineraryStop.objects.create(
                    itinerary=trip, place=place,
                    start_time=arrival, stop_order=position, notes=notes,
                )
                messages.success(request, 'Destination added to your itinerary.')
        return redirect('itineraries:builder', pk=trip.pk)

    trips = (Itinerary.objects.filter(user=request.user, city_id=CITY_ID)
             .annotate(stop_count=Count('stops'),
                       already_added=Exists(
                           ItineraryStop.objects.filter(
                               itinerary_id=OuterRef('pk'), place_id=place.pk)))
             .order_by('-updated_at', '-pk'))
    return render(request, 'itineraries/choose_for_place.html', {
        'place': place, 'trips': trips,
    })
