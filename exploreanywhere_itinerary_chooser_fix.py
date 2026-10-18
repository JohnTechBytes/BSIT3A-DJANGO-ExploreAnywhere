#!/usr/bin/env python3
"""ExploreAnywhere — Saved Places -> Choose Existing Itinerary (Phase 4D prep).

Run inside the Django project root:
    python "$env:USERPROFILE\\Downloads\\exploreanywhere_itinerary_chooser_fix.py"

Adds a user-owned Kabankalan-only itinerary picker, preserving existing CRUD,
CSRF, models, data and migration history. All changes are backed up and checked.
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

ROOT = Path.cwd()
VIEWS = Path('apps/itineraries/views.py')
URLS = Path('apps/itineraries/urls.py')
SAVED = Path('templates/places/saved_places.html')
DETAIL = Path('templates/places/place_detail.html')
CHOOSER = Path('templates/itineraries/choose_for_place.html')
MARKER = '# exploreanywhere-itinerary-chooser-v1'

NEW_VIEW = '''

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
'''

NEW_ROUTE = '    path("add-place/<int:place_id>/", views.choose_for_place, name="choose_for_place"),  # exploreanywhere-itinerary-chooser-v1\n'

NEW_TEMPLATE = '''{% extends "theme/public_base.html" %}
{% block extra_css %}
<style>
/* exploreanywhere-itinerary-chooser-v1 */
.ea-choose {max-width:990px;margin:0 auto;padding:36px 20px 100px;color:#12365e}
.ea-choose * {box-sizing:border-box}
.ea-choose .hero {background:linear-gradient(120deg,#083366,#096ee7);color:white;border-radius:23px;padding:clamp(24px,4vw,38px);margin-bottom:24px}
.ea-choose .eyebrow {font-size:12px;letter-spacing:.11em;font-weight:800;color:#c8e0ff}
.ea-choose h1 {color:#fff;font-size:clamp(28px,4vw,39px);line-height:1.15;margin:10px 0}
.ea-choose .hero p {color:#eaf3ff;margin:6px 0 0}
.ea-choose .place {background:#eaf3ff;border:1px solid #cfe1f9;border-radius:15px;padding:15px 18px;margin-bottom:22px;color:#124174}
.ea-choose .place strong {font-size:19px;display:block;margin:5px 0}
.ea-choose h2 {font-size:21px;font-weight:800;color:#12365e;margin:15px 0}
.ea-choose .card {background:#fff;border:1px solid #d8e6f5;border-radius:18px;padding:clamp(17px,3vw,26px);margin-bottom:16px;box-shadow:0 8px 22px rgba(16,47,89,.04)}
.ea-choose .card:focus-within {border-color:#287be5}
.ea-choose .title {font-size:18px;font-weight:800;color:#12365e;margin:0 0 3px;overflow-wrap:anywhere}
.ea-choose .muted {color:#60778e;font-size:13px;line-height:1.55}
.ea-choose .grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:15px}
.ea-choose label {display:block;font-size:13px;font-weight:800;color:#24486d;margin-bottom:6px}
.ea-choose input {width:100%;min-height:44px;padding:11px 12px;border:1px solid #c5d6ea;border-radius:10px;font:inherit;background:white;color:#14345d}
.ea-choose .buttons {display:flex;gap:10px;flex-wrap:wrap;margin-top:14px}
.ea-choose .btn {display:inline-flex;justify-content:center;align-items:center;min-height:44px;padding:10px 16px;text-decoration:none;font:inherit;font-size:14px;font-weight:800;border:1px solid #075ee4;border-radius:10px;background:#075ee4;color:#fff;cursor:pointer}
.ea-choose .btn.secondary {background:#fff;color:#0757d8;border-color:#bfd3ed}
.ea-choose .btn:focus-visible,.ea-choose input:focus-visible {outline:3px solid #f2b845;outline-offset:3px}
.ea-choose .pill {display:inline-block;background:#e8f4ff;padding:5px 11px;border-radius:100px;color:#0757d8;font-size:12px;font-weight:800}
.ea-choose .already {color:#0a7051;background:#edfff6;padding:12px 14px;border-radius:10px;margin-top:13px}
.ea-choose .empty {border:1px dashed #b4cee9;padding:26px;border-radius:16px;background:#f5faff}
.ea-choose .messages {list-style:none;margin:0 0 17px;padding:0}
.ea-choose .messages li {padding:12px 15px;background:#eef5ff;border-left:4px solid #075ee4;border-radius:10px;color:#174570;margin:7px 0}
@media(max-width:680px) {.ea-choose{padding:22px 14px 70px}.ea-choose .grid{grid-template-columns:1fr}.ea-choose .buttons .btn{width:100%}}
@media(prefers-reduced-motion:reduce){.ea-choose *{scroll-behavior:auto}}
</style>
{% endblock %}
{% block content %}
<main class="ea-choose">
  <header class="hero">
    <span class="eyebrow">MY KABANKALAN JOURNEY · ITINERARIES</span>
    <h1>Add to an Itinerary</h1>
    <p>Choose an existing trip, or create a new one. No trip will be created just by opening this page.</p>
  </header>
  {% if messages %}<ul class="messages" aria-live="polite">{% for message in messages %}<li>{{ message }}</li>{% endfor %}</ul>{% endif %}
  <section class="place" aria-label="Selected destination">
    <small>YOUR SELECTED KABANKALAN DESTINATION</small>
    <strong>{{ place.title }}</strong>
    <span class="muted">{{ place.category|default:"Destination" }} · Kabankalan, Negros Occidental</span>
  </section>
  <h2>Choose one of your plans</h2>
  {% if trips %}
    {% for trip in trips %}
    <article class="card">
      <span class="pill">Day {{ trip.day_number }} · {{ trip.stop_count }} stop{{ trip.stop_count|pluralize }}</span>
      <h3 class="title">{{ trip.title }}</h3>
      {% if trip.already_added %}
        <p class="already">This destination is already in this itinerary.</p>
        <div class="buttons"><a class="btn secondary" href="{% url 'itineraries:builder' trip.pk %}">View Existing Plan</a></div>
      {% else %}
        <form method="post" action="{% url 'itineraries:choose_for_place' place.pk %}">
          {% csrf_token %}
          <input type="hidden" name="itinerary_id" value="{{ trip.pk }}">
          <div class="grid">
            <div><label for="time-{{ trip.pk }}">Planned arrival time</label><input id="time-{{ trip.pk }}" name="start_time" type="time" value="09:00" required></div>
            <div><label for="note-{{ trip.pk }}">Optional stop notes</label><input id="note-{{ trip.pk }}" name="notes" maxlength="255" placeholder="What would you like to do here?"></div>
          </div>
          <div class="buttons"><button class="btn" type="submit">Add to {{ trip.title }}</button><a class="btn secondary" href="{% url 'itineraries:builder' trip.pk %}">View Plan</a></div>
        </form>
      {% endif %}
    </article>
    {% endfor %}
  {% else %}
    <div class="empty"><p>You have no itineraries yet. Create your first trip with this destination preselected.</p></div>
  {% endif %}
  <section class="card" aria-label="Create a new itinerary">
    <h2>Need a new trip?</h2>
    <p class="muted">Create a separately named itinerary and add {{ place.title }} as its first stop.</p>
    <div class="buttons"><a class="btn" href="{% url 'itineraries:create' %}?place={{ place.pk }}">+ Create New Itinerary</a><a class="btn secondary" href="{% url 'places:saved_places' %}">Back to Saved Places</a></div>
  </section>
</main>
{% endblock %}
'''


def require_exactly_one(content: str, old: str, label: str) -> None:
    actual = content.count(old)
    if actual != 1:
        raise ValueError(f'Unexpected {label}: found {actual} expected 1. No changes made.')


def main() -> int:
    if not (ROOT / 'manage.py').is_file():
        print('ERROR: Run the script from the ExploreAnywhere project folder containing manage.py.')
        return 1
    required = [VIEWS, URLS, SAVED]
    for rel in required:
        if not (ROOT / rel).is_file():
            print(f'ERROR: Missing required file: {rel}')
            return 1
    originals = {rel: (ROOT / rel).read_text(encoding='utf-8-sig') for rel in required}
    data = originals
    if MARKER in data[VIEWS] or 'choose_for_place' in data[URLS]:
        if MARKER in data[VIEWS] and 'choose_for_place' in data[URLS] and (ROOT / CHOOSER).is_file():
            print('ALREADY INSTALLED: The itinerary chooser is present. No changes made.')
            return 0
        print('ERROR: Found a partial existing chooser installation. No changes made.')
        return 1
    if (ROOT / CHOOSER).exists():
        print('ERROR: Itinerary chooser template already exists. Refusing to overwrite it.')
        return 1
    views = data[VIEWS]
    urls = data[URLS]
    saved = data[SAVED]
    old_saved = 'href="{% url \'itineraries:create\' %}?place={{ entry.place.pk }}"'
    try:
        for text in ('def create_itinerary(', 'def add_stop(', 'def _places():', 'CITY_ID = 2', 'from django.db import transaction', 'from django.contrib import messages'):
            if text not in views:
                raise ValueError(f'Unrecognized existing itinerary views: missing {text}')
        require_exactly_one(saved, old_saved, 'Saved Places Add to Itinerary link')
        require_exactly_one(urls, '    path("new/", views.create_itinerary, name="create"),\n', 'Itinerary URL insertion anchor')
        if '{% extends "theme/public_base.html" %}' not in saved or '{% csrf_token %}' not in saved:
            raise ValueError('Unexpected Saved Places template structure.')
        new_views = views.rstrip() + '\n' + NEW_VIEW
        new_urls = urls.replace(
            '    path("new/", views.create_itinerary, name="create"),\n',
            '    path("new/", views.create_itinerary, name="create"),\n' + NEW_ROUTE, 1,
        )
        new_saved = saved.replace(old_saved,
            'href="{% url \'itineraries:choose_for_place\' entry.place.pk %}"', 1)
        ast.parse(new_views, filename=str(VIEWS))
        ast.parse(new_urls, filename=str(URLS))
        if new_saved.count("{% url 'itineraries:choose_for_place' entry.place.pk %}") != 1:
            raise ValueError('Could not validate the updated Saved Places link.')
        if NEW_TEMPLATE.count('{% csrf_token %}') != 1 or NEW_TEMPLATE.count('{% endblock %}') != 2:
            raise ValueError('Could not validate the chooser template.')
    except (SyntaxError, ValueError) as exc:
        print('ERROR:', exc)
        return 1

    updates = {VIEWS: new_views, URLS: new_urls, SAVED: new_saved, CHOOSER: NEW_TEMPLATE}
    detail_path = ROOT / DETAIL
    if detail_path.is_file():
        detail_current = detail_path.read_text(encoding='utf-8-sig')
        old_detail = 'href="{% url \'itineraries:create\' %}?place={{ place.pk }}"'
        if detail_current.count(old_detail) == 1:
            updates[DETAIL] = detail_current.replace(old_detail,
                'href="{% url \'itineraries:choose_for_place\' place.pk %}"', 1)
        elif detail_current.count(old_detail) > 1:
            print('ERROR: Unexpected repeated Add to Itinerary links in place_detail.html; no changes made.')
            return 1

    backup = ROOT / 'phase4_backups' / ('itinerary-chooser-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    try:
        for rel in updates:
            if (ROOT / rel).exists():
                target = backup / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, target)
        written = []
        try:
            for rel, content in updates.items():
                target = ROOT / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding='utf-8', newline='\n')
                written.append(rel)
        except Exception:
            for rel in reversed(written):
                dest = ROOT / rel
                source = backup / rel
                if source.is_file():
                    shutil.copy2(source, dest)
                elif dest.exists():
                    dest.unlink()
            raise
    except Exception as exc:
        print(f'ERROR writing files: {exc}')
        return 1

    print('SUCCESS: Add to Itinerary chooser installed.')
    print('Saved Places now lets users select an existing trip or explicitly create a new one.')
    print('Owned-trip checks, published Kabankalan filtering, and CSRF protection retained.')
    print('No existing itineraries were removed, renamed, or modified.')
    print(f'Backup: {backup.relative_to(ROOT)}')
    print('New route: /itineraries/add-place/<place_id>/')
    print('Next: python manage.py check')
    print('Next: python manage.py shell -c "from django.template.loader import get_template; get_template(\'itineraries/choose_for_place.html\'); print(\'Template OK\')"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
