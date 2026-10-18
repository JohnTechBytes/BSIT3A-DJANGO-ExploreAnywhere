#!/usr/bin/env python3
"""ExploreAnywhere: Kabankalan City Edition — Phase 3D itinerary integration.

Run in the Django project root. Preflight validation, backup, and rollback.
Adds functional itinerary routes, private CRUD views, templates, and links
from existing Saved Places and Journey pages. No migrations/data changes.
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
MARK = 'ExploreAnywhere phase3d itinerary integration v1'
APP_VIEWS = Path('apps/itineraries/views.py')
APP_URLS = Path('apps/itineraries/urls.py')
ROOT_URLS = Path('mysite/urls.py')
MODELS = Path('apps/itineraries/models.py')
LIST_TMPL = Path('templates/itineraries/my_itineraries.html')
CREATE_TMPL = Path('templates/itineraries/create.html')
BUILDER_TMPL = Path('templates/itineraries/builder.html')
SAVED_TMPL = Path('templates/places/saved_places.html')
JOURNEY_TMPL = Path('templates/places/journey_dashboard.html')
DETAIL_TMPL = Path('templates/places/place_detail.html')

VIEWS = r'''"""Kabankalan-only, user-owned itinerary planning (Phase 3D)."""
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
'''

URLS = '''"""Kabankalan itinerary routes — Phase 3D."""
from django.urls import path
from . import views

app_name = "itineraries"

urlpatterns = [
    path("", views.my_itineraries, name="list"),
    path("new/", views.create_itinerary, name="create"),
    path("<int:pk>/", views.builder, name="builder"),
    path("<int:pk>/update/", views.update_itinerary, name="update"),
    path("<int:pk>/delete/", views.delete_itinerary, name="delete"),
    path("<int:pk>/stops/add/", views.add_stop, name="add_stop"),
    path("<int:pk>/stops/<int:stop_id>/update/", views.update_stop, name="update_stop"),
    path("<int:pk>/stops/<int:stop_id>/remove/", views.remove_stop, name="remove_stop"),
    path("<int:pk>/stops/<int:stop_id>/move/", views.move_stop, name="move_stop"),
]
'''

CSS = '''
.ea-trip{max-width:1100px;margin:auto;padding:38px 20px 92px;color:#12345b}
.ea-trip h1{font-size:clamp(28px,4vw,40px);font-weight:800;color:#102f59;margin:8px 0 14px}
.ea-trip h2{font-size:20px;color:#13365e;margin:0 0 12px}
.ea-trip p,.ea-trip small{color:#637993;line-height:1.6}
.ea-trip .eyebrow{font-size:12px;font-weight:800;letter-spacing:.12em;color:#0757d8;text-transform:uppercase}
.ea-trip .panel{background:#fff;border:1px solid #dce8f5;border-radius:18px;padding:22px;margin:16px 0;box-shadow:0 8px 22px rgba(20,47,80,.04)}
.ea-trip .hero{background:linear-gradient(115deg,#102f64,#075ee4);color:white;border-radius:18px;padding:26px;margin-bottom:20px}
.ea-trip .hero h1,.ea-trip .hero p{color:white}.ea-trip .hero p{opacity:.9;margin:0}
.ea-trip .actions{display:flex;align-items:center;flex-wrap:wrap;gap:9px;margin:16px 0}
.ea-trip .btn{display:inline-flex;justify-content:center;align-items:center;text-decoration:none;background:#075ee4;border:1px solid #075ee4;color:#fff!important;border-radius:10px;padding:10px 15px;min-height:42px;font:inherit;font-size:13px;font-weight:700;cursor:pointer}
.ea-trip .btn.outline{background:#fff;color:#0757d8!important;border-color:#bdd3ef}.ea-trip .btn.danger{background:#fff;color:#a51e35!important;border-color:#efbac6}
.ea-trip .grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}
.ea-trip .trip-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px}
.ea-trip .field{display:flex;flex-direction:column;gap:6px;margin-bottom:13px}.ea-trip .field label{font-size:13px;font-weight:700;color:#254b73}
.ea-trip input,.ea-trip select,.ea-trip textarea{width:100%;border:1px solid #c9d7e9;border-radius:10px;padding:11px 12px;color:#16375c;background:#fff;font:inherit;font-size:14px}
.ea-trip .muted{color:#637993;font-size:13px}.ea-trip .pill{display:inline-block;background:#e8f2ff;color:#0757d8;padding:5px 9px;border-radius:99px;font-size:12px;font-weight:700}
.ea-trip .stop{border-left:4px solid #075ee4}.ea-trip .stop-head{display:flex;justify-content:space-between;gap:8px;align-items:flex-start}
.ea-trip .stop h3{font-size:18px;margin:4px 0;color:#12385f}.ea-trip .stop .mini-actions{display:flex;gap:8px;flex-wrap:wrap}
.ea-trip .stop .mini-actions form,.ea-trip .actions form{margin:0}
.ea-trip .messages{list-style:none;padding:0;margin:0 0 16px}.ea-trip .messages li{padding:12px;background:#eaf3ff;color:#143f75;border-radius:10px;margin:8px 0}
.ea-trip .empty{border:1px dashed #b9cfe8;border-radius:16px;padding:26px;background:white}
@media(max-width:720px){.ea-trip{padding:22px 14px 72px}.ea-trip .grid{grid-template-columns:1fr}.ea-trip .panel{padding:17px}}
'''

LIST = '''{% extends "theme/public_base.html" %}
{% block extra_css %}<style>__CSS__</style>{% endblock %}
{% block content %}
<main class="ea-trip">
  <div class="hero"><p>MY KABANKALAN JOURNEY</p><h1>My Itineraries</h1><p>Build a personal plan from real, published Kabankalan destinations.</p></div>
  {% if messages %}<ul class="messages" aria-live="polite">{% for message in messages %}<li>{{ message }}</li>{% endfor %}</ul>{% endif %}
  <nav class="actions" aria-label="Itinerary navigation">
    <a class="btn" href="{% url 'itineraries:create' %}">+ Create Itinerary</a>
    <a class="btn outline" href="{% url 'places:journey_dashboard' %}">My Journey</a>
    <a class="btn outline" href="{% url 'places:saved_places' %}">Saved Places</a>
  </nav>
  {% if trips %}
  <section class="trip-cards" aria-label="Your itineraries">
    {% for trip in trips %}
    <article class="panel"><span class="pill">Day {{ trip.day_number }}</span><h2>{{ trip.title }}</h2>
      <p>{{ trip.stop_count }} planned stop{{ trip.stop_count|pluralize }}</p>
      <p class="muted">Updated {{ trip.updated_at|date:"M j, Y" }}</p>
      <a class="btn" href="{% url 'itineraries:builder' trip.pk %}">View / Edit Plan</a>
    </article>
    {% endfor %}
  </section>
  {% else %}
  <section class="empty"><h2>No itinerary yet</h2><p>Create a Kabankalan itinerary and add places you want to visit.</p><a class="btn" href="{% url 'itineraries:create' %}">Create Your First Itinerary</a></section>
  {% endif %}
</main>
{% endblock %}
'''.replace('__CSS__', CSS)

CREATE = '''{% extends "theme/public_base.html" %}
{% block extra_css %}<style>__CSS__</style>{% endblock %}
{% block content %}
<main class="ea-trip">
  <p class="eyebrow">ONE CITY. YOUR HOBBIES. OUR MAP.</p><h1>Create a Kabankalan Itinerary</h1>
  <p>Choose a title and optionally add your first destination. Times are plans, not estimated travel times or confirmed visits.</p>
  {% if messages %}<ul class="messages" aria-live="polite">{% for message in messages %}<li>{{ message }}</li>{% endfor %}</ul>{% endif %}
  <div class="panel">
    <form method="post" action="{% url 'itineraries:create' %}">{% csrf_token %}
      <div class="grid"><div class="field"><label for="trip-title">Trip title</label><input id="trip-title" name="title" maxlength="255" required value="{{ input_title }}" placeholder="My Kabankalan Day Trip"></div>
      <div class="field"><label for="trip-day">Day number</label><input id="trip-day" type="number" name="day_number" min="1" max="365" value="{{ input_day }}" required></div></div>
      <div class="grid"><div class="field"><label for="initial-place">First destination (optional)</label>
        <select id="initial-place" name="initial_place"><option value="">Create an empty itinerary</option>
          {% for place in places %}<option value="{{ place.pk }}" {% if selected_place == place.pk|stringformat:"s" %}selected{% endif %}>{{ place.title }}</option>{% endfor %}
        </select><small>Only active, verified Kabankalan destinations are listed.</small></div>
      <div class="field"><label for="first-time">Planned arrival time (when selecting a destination)</label><input id="first-time" type="time" name="start_time" value="{{ input_time }}"></div></div>
      <div class="actions"><button class="btn" type="submit">Create Itinerary</button><a class="btn outline" href="{% url 'itineraries:list' %}">Cancel</a></div>
    </form>
  </div>
</main>
{% endblock %}
'''.replace('__CSS__', CSS)

BUILDER = '''{% extends "theme/public_base.html" %}
{% block extra_css %}<style>__CSS__</style>{% endblock %}
{% block content %}
<main class="ea-trip">
  <div class="hero"><p>MY KABANKALAN JOURNEY · TRIP PLANNER</p><h1>{{ trip.title }}</h1><p>Day {{ trip.day_number }} · Kabankalan, Negros Occidental</p></div>
  {% if messages %}<ul class="messages" aria-live="polite">{% for message in messages %}<li>{{ message }}</li>{% endfor %}</ul>{% endif %}
  <nav class="actions" aria-label="Itinerary navigation"><a class="btn outline" href="{% url 'itineraries:list' %}">All Itineraries</a><a class="btn outline" href="{% url 'places:journey_dashboard' %}">My Journey</a><a class="btn outline" href="{% url 'places:saved_places' %}">Saved Places</a></nav>
  <div class="grid"><section class="panel"><h2>Trip Information</h2>
    <form method="post" action="{% url 'itineraries:update' trip.pk %}">{% csrf_token %}
      <div class="field"><label for="edit-title">Trip title</label><input id="edit-title" name="title" value="{{ trip.title }}" maxlength="255" required></div>
      <div class="field"><label for="edit-day">Day number</label><input id="edit-day" type="number" name="day_number" min="1" max="365" value="{{ trip.day_number }}" required></div>
      <button class="btn" type="submit">Save Trip Details</button>
    </form></section>
    <section class="panel"><h2>Add a Destination</h2>
      <form method="post" action="{% url 'itineraries:add_stop' trip.pk %}">{% csrf_token %}
        <div class="field"><label for="add-place">Kabankalan place</label><select id="add-place" name="place_id" required><option value="">Choose a destination</option>
          {% for place in places %}<option value="{{ place.pk }}">{{ place.title }}</option>{% endfor %}</select></div>
        <div class="field"><label for="add-time">Planned arrival time</label><input id="add-time" type="time" name="start_time" value="09:00" required></div>
        <div class="field"><label for="add-note">Notes (optional)</label><input id="add-note" name="notes" maxlength="255" placeholder="What would you like to do here?"></div>
        <button class="btn" type="submit">+ Add Stop</button>
      </form>
      <p class="muted">Adding a stop is a plan, not confirmation that you visited.</p>
    </section></div>
  <section aria-label="Scheduled itinerary stops"><h2>Your Planned Stops ({{ stops|length }})</h2>
    {% if stops %}<div class="trip-cards">{% for stop in stops %}
      <article class="panel stop"><div class="stop-head"><div><span class="pill">Stop {{ stop.stop_order }}</span><h3>{{ stop.place.title }}</h3></div>
      <div class="mini-actions">
        <form method="post" action="{% url 'itineraries:move_stop' trip.pk stop.pk %}">{% csrf_token %}<input type="hidden" name="direction" value="up"><button type="submit" class="btn outline" aria-label="Move {{ stop.place.title }} up">↑</button></form>
        <form method="post" action="{% url 'itineraries:move_stop' trip.pk stop.pk %}">{% csrf_token %}<input type="hidden" name="direction" value="down"><button type="submit" class="btn outline" aria-label="Move {{ stop.place.title }} down">↓</button></form>
      </div></div>
      <p class="muted">Kabankalan{% if not stop.place.is_verified or not stop.place.is_active %} · Currently unpublished{% endif %}</p>
      <form method="post" action="{% url 'itineraries:update_stop' trip.pk stop.pk %}">{% csrf_token %}
        <div class="field"><label for="time-{{ stop.pk }}">Planned arrival time</label><input id="time-{{ stop.pk }}" type="time" name="start_time" value="{{ stop.start_time|time:'H:i' }}" required></div>
        <div class="field"><label for="notes-{{ stop.pk }}">Stop notes</label><input id="notes-{{ stop.pk }}" name="notes" value="{{ stop.notes }}" maxlength="255"></div>
        <button class="btn outline" type="submit">Save Stop</button>
      </form>
      <div class="actions">{% if stop.place.is_active and stop.place.is_verified %}<a class="btn outline" href="{% url 'places:place_detail' stop.place.pk %}">Place Details</a>{% endif %}
      {% if stop.place.latitude != None and stop.place.longitude != None %}<a class="btn outline" href="https://www.google.com/maps/search/?api=1&amp;query={{ stop.place.latitude }},{{ stop.place.longitude }}" target="_blank" rel="noopener noreferrer">View on Map ↗</a>{% endif %}
      <form method="post" action="{% url 'itineraries:remove_stop' trip.pk stop.pk %}" onsubmit="return confirm('Remove this stop?');">{% csrf_token %}<button type="submit" class="btn danger">Remove Stop</button></form></div>
      </article>{% endfor %}</div>
    {% else %}<div class="empty"><h2>No stops yet</h2><p>Use the Add a Destination form above to plan your first stop.</p></div>{% endif %}
  </section>
  <section class="panel"><h2>Manage Itinerary</h2><p>This permanently removes the trip and its planned stops, but does not remove your Saved Places.</p>
    <form method="post" action="{% url 'itineraries:delete' trip.pk %}" onsubmit="return confirm('Delete this entire itinerary? This cannot be undone.');">{% csrf_token %}<button class="btn danger" type="submit">Delete Itinerary</button></form>
  </section>
</main>
{% endblock %}
'''.replace('__CSS__', CSS)


def fail(reason):
    raise RuntimeError(reason)


def main():
    required = (APP_VIEWS, APP_URLS, ROOT_URLS, MODELS, LIST_TMPL, BUILDER_TMPL, SAVED_TMPL, JOURNEY_TMPL)
    for path in required:
        if not (ROOT / path).is_file():
            fail(f'Missing {path}; run from the ExploreAnywhere project root.')
    current = {path: (ROOT / path).read_text(encoding='utf-8-sig') for path in required}
    models = current[MODELS]
    for item in ('class Itinerary(', 'class ItineraryStop(', 'start_time = models.TimeField()', 'day_number = models.PositiveIntegerField('):
        if item not in models:
            fail(f'Itinerary schema differs from audited source: {item}')
    for path in (APP_URLS, APP_VIEWS, LIST_TMPL, BUILDER_TMPL):
        if current[path].strip():
            fail(f'{path} is no longer empty. No files changed; needs review.')
    if (ROOT / CREATE_TMPL).exists() and (ROOT / CREATE_TMPL).stat().st_size:
        fail(f'{CREATE_TMPL} already contains content. No files changed.')

    root_urls = current[ROOT_URLS]
    if 'include(' not in root_urls or 'urlpatterns' not in root_urls:
        fail('Cannot safely update mysite/urls.py; unexpected structure.')
    if 'apps.itineraries.urls' in root_urls:
        fail('Itinerary URLs already included; please review current routes first.')
    match = re.search(r'(?m)^urlpatterns\s*=\s*\[', root_urls)
    if not match:
        fail('Cannot find urlpatterns list to add route.')
    # Insert at the start so unrelated existing app routes remain unchanged.
    root_new = root_urls[:match.end()] + "\n    path('itineraries/', include('apps.itineraries.urls')),  # " + MARK + root_urls[match.end():]
    try:
        ast.parse(root_new)
    except SyntaxError as ex:
        fail(f'Generated project URL code did not compile: {ex}')

    saved_old = current[SAVED_TMPL]
    journey_old = current[JOURNEY_TMPL]
    saved_anchor = '<a class="ea-action" href="{% url \'places:place_detail\' entry.place.pk %}">View Details</a>'
    if saved_old.count(saved_anchor) != 1:
        fail('Saved Places card markup changed: cannot add itinerary link safely.')
    saved_new = saved_old.replace(saved_anchor,
       saved_anchor + '\n      <a class="ea-action ea-action-secondary" href="{% url \'itineraries:create\' %}?place={{ entry.place.pk }}">Add to Itinerary</a>', 1)
    journey_anchor = '<div class="ea-journey-item">{{ trip.title }}{% if trip.day_number %} · Day {{ trip.day_number }}{% endif %}</div>'
    journey_note = '<p class="ea-journey-note">Plan editing will be connected to the existing itinerary builder in the next step.</p>'
    if journey_old.count(journey_anchor) != 1 or journey_old.count(journey_note) != 1:
        fail('Journey dashboard markup changed: cannot connect itinerary links safely.')
    journey_new = journey_old.replace(journey_anchor,
        '<a class="ea-journey-item" href="{% url \'itineraries:builder\' trip.pk %}">{{ trip.title }}{% if trip.day_number %} · Day {{ trip.day_number }}{% endif %}</a>', 1)
    journey_new = journey_new.replace(journey_note,
        '<div class="ea-journey-actions"><a class="ea-journey-link" href="{% url \'itineraries:create\' %}">+ Create Itinerary</a> <a class="ea-journey-link" href="{% url \'itineraries:list\' %}">View All Plans</a></div>', 1)

    updates = {
        APP_VIEWS: VIEWS, APP_URLS: URLS, LIST_TMPL: LIST, BUILDER_TMPL: BUILDER,
        CREATE_TMPL: CREATE, ROOT_URLS: root_new,
        SAVED_TMPL: saved_new, JOURNEY_TMPL: journey_new,
    }
    detail_path = ROOT / DETAIL_TMPL
    if detail_path.is_file():
        detail_old = detail_path.read_text(encoding='utf-8-sig')
        detail_anchor = '<a href="{% url \'places:saved_places\' %}">My Saved Places</a>'
        if detail_anchor in detail_old and 'itineraries:create' not in detail_old:
            updates[DETAIL_TMPL] = detail_old.replace(
                detail_anchor, '<a href="{% url \'itineraries:create\' %}?place={{ place.pk }}">Add to Itinerary</a>\n      ' + detail_anchor, 1)

    for path, content in updates.items():
        if path.suffix == '.py':
            ast.parse(content, filename=str(path))
        if path.suffix == '.html':
            if content.count('{% block content %}') != 1 or content.count('{% endblock %}') < 1:
                fail(f'Generated HTML block check failed: {path}')
    # Back up every existing file, including the intentionally empty source files.
    backup = ROOT / 'phase3_backups' / ('itineraries-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    existed = {p: (ROOT / p).exists() for p in updates}
    for p, present in existed.items():
        if present:
            dest = backup / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / p, dest)
    touched = []
    try:
        for p, content in updates.items():
            dest = ROOT / p
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(content, encoding='utf-8', newline='\n')
            touched.append(p)
    except Exception:
        for p in reversed(touched):
            if existed[p]:
                shutil.copy2(backup / p, ROOT / p)
            else:
                (ROOT / p).unlink(missing_ok=True)
        raise
    print('SUCCESS: Phase 3D itinerary planner installed.')
    print('Added trip creation, editing, planned stops, ordering, removal, and deletion.')
    print('Linked Saved Places, My Kabankalan Journey, and Place Details (when matching).')
    print('No database records or migrations were changed.')
    print('Backup directory:', backup.relative_to(ROOT))
    print('Routes: /itineraries/  /itineraries/new/  /itineraries/<id>/')
    print('Next: python manage.py check')
    print('Next: python manage.py shell -c "from django.template.loader import get_template; [get_template(x) for x in [\'itineraries/create.html\',\'itineraries/builder.html\',\'itineraries/my_itineraries.html\']]; print(\'Templates OK\')"')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STOPPED:', exc, file=sys.stderr)
        sys.exit(1)
