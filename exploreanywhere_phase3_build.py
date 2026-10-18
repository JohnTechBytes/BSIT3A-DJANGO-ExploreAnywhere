#!/usr/bin/env python3
"""ExploreAnywhere Phase 3: non-destructive Saved Places + Journey starter.

Run from the Django project root. No migrations or database writes are performed.
The resulting Django views perform user-requested Save/Unsave POST actions.
"""
from __future__ import annotations

import ast
from datetime import datetime
from pathlib import Path
import shutil
import sys

ROOT = Path.cwd()
URLS = Path('apps/places/urls.py')
VIEWS = Path('apps/places/views.py')
DETAIL = Path('templates/places/place_detail.html')
MODELS = Path('apps/places/models.py')
JOURNEY_VIEWS = Path('apps/places/journey_views.py')
SAVED = Path('templates/places/saved_places.html')
DASHBOARD = Path('templates/places/journey_dashboard.html')
MARKER = 'ExploreAnywhere phase3 save-and-journey v1'


NEW_VIEWS = '''"""ExploreAnywhere phase3 save-and-journey v1.

All public place collections are restricted to verified, active Kabankalan places.
Saving and unsaving use POST + CSRF, with data scoped to the current user.
"""
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Place, Review, SavedPlace

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
    return render(request, "places/journey_dashboard.html", {
        "saved_count": saved.count(),
        "saved_preview": saved[:4],
        "itinerary_count": itineraries.count(),
        "itinerary_preview": itineraries[:4],
        "review_count": review_count,
    })
'''

NEW_SAVED = '''{% extends "theme/public_base.html" %}
{% block extra_css %}
<style>
.ea-saved {max-width:1080px;margin:auto;padding:40px 20px 90px;color:#142e50}
.ea-saved h1 {font-size:clamp(28px,4vw,40px);font-weight:800;margin:12px 0}
.ea-muted {color:#61748d;line-height:1.6}
.ea-actions {display:flex;gap:10px;flex-wrap:wrap;margin:20px 0 28px}
.ea-action {background:#075ee4;color:white!important;padding:11px 17px;border-radius:11px;text-decoration:none;font-weight:700;display:inline-block}
.ea-action-secondary {background:white;color:#0757d8!important;border:1px solid #cbdaf0}
.ea-saved-grid {display:grid;grid-template-columns:repeat(auto-fill,minmax(245px,1fr));gap:16px}
.ea-saved-item {background:white;border:1px solid #dfe8f4;border-radius:17px;padding:19px;box-shadow:0 6px 22px rgba(20,53,93,.05);display:flex;flex-direction:column;gap:10px}
.ea-saved-item h2 {font-size:20px;color:#14345b;margin:0}
.ea-saved-item p {font-size:13px;margin:0}
.ea-saved-item form {margin-top:auto}
.ea-unsave {cursor:pointer;background:#fff;border:1px solid #b7c9e6;border-radius:10px;padding:10px 13px;color:#174c8a;font-weight:700;width:100%}
.ea-empty {background:white;border:1px dashed #b6c8df;padding:35px;border-radius:16px}
</style>
{% endblock %}
{% block content %}
<main class="ea-saved">
  <p class="ea-muted">MY KABANKALAN JOURNEY</p>
  <h1>Saved Places</h1>
  <p class="ea-muted">Your personal collection of published Kabankalan destinations.</p>
  <nav class="ea-actions" aria-label="Saved places navigation">
    <a class="ea-action" href="{% url 'places:journey_dashboard' %}">My Journey</a>
    <a class="ea-action ea-action-secondary" href="{% url 'places:attraction_carousel' %}">Explore Recommendations</a>
  </nav>
  {% if entries %}
  <section class="ea-saved-grid" aria-label="Your saved destinations">
    {% for entry in entries %}
    <article class="ea-saved-item">
      <h2>{{ entry.place.title }}</h2>
      <p class="ea-muted">{% if entry.place.category %}{{ entry.place.category.name }} · {% endif %}Kabankalan, Negros Occidental</p>
      <p class="ea-muted">{{ entry.place.description|default:"Destination information coming soon."|truncatechars:130 }}</p>
      <a class="ea-action" href="{% url 'places:place_detail' entry.place.pk %}">View Details</a>
      <form method="post" action="{% url 'places:unsave_place' entry.place.pk %}">
        {% csrf_token %}
        <button class="ea-unsave" type="submit">Remove from Saved</button>
      </form>
    </article>
    {% endfor %}
  </section>
  {% else %}
  <div class="ea-empty"><h2>No saved places yet</h2><p class="ea-muted">Discover a destination and select Save Place to add it here.</p></div>
  {% endif %}
</main>
{% endblock %}
'''

NEW_DASHBOARD = '''{% extends "theme/public_base.html" %}
{% block extra_css %}
<style>
.ea-journey {max-width:1100px;margin:auto;padding:45px 20px 100px;color:#173454}
.ea-journey h1 {font-size:clamp(30px,4vw,44px);margin:9px 0;font-weight:850;color:#10315b}
.ea-journey p {color:#62748b;line-height:1.65}
.ea-journey-top {background:linear-gradient(125deg,#102f64,#075ee4);border-radius:20px;padding:28px;color:white}
.ea-journey-top h1,.ea-journey-top p {color:white}
.ea-journey-top p {opacity:.86}
.ea-journey-metrics {display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:14px;margin:21px 0 30px}
.ea-journey-metric {background:white;border:1px solid #dce7f3;border-radius:15px;padding:22px}
.ea-journey-metric strong {display:block;color:#0757d8;font-size:32px}
.ea-journey-metric span {color:#64748b;font-size:13px}
.ea-journey-grid {display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:18px}
.ea-journey-panel {background:white;border:1px solid #dce7f3;border-radius:18px;padding:23px}
.ea-journey-panel h2 {font-size:19px;color:#16375d;margin:0 0 12px}
.ea-journey-item {display:block;padding:12px 0;border-bottom:1px solid #ebf1f7;color:#13519a;text-decoration:none;font-weight:700}
.ea-journey-item:last-child {border-bottom:0}
.ea-journey-link {display:inline-block;background:#075ee4;border-radius:11px;color:white!important;text-decoration:none;padding:11px 16px;font-weight:700;margin-top:14px}
.ea-journey-note {background:#f1f6fc;border-radius:12px;padding:12px;font-size:13px;color:#4d647e}
@media(max-width:680px){.ea-journey-metrics,.ea-journey-grid{grid-template-columns:1fr}}
</style>
{% endblock %}
{% block content %}
<main class="ea-journey">
  <header class="ea-journey-top">
    <p>ONE CITY. YOUR HOBBIES. OUR MAP.</p>
    <h1>My Kabankalan Journey</h1>
    <p>Welcome back! Organize places you love and return to your Kabankalan plans.</p>
  </header>
  <section class="ea-journey-metrics" aria-label="Your journey summary">
    <div class="ea-journey-metric"><strong>{{ saved_count }}</strong><span>Saved destinations</span></div>
    <div class="ea-journey-metric"><strong>{{ itinerary_count }}</strong><span>Planned itineraries</span></div>
    <div class="ea-journey-metric"><strong>{{ review_count }}</strong><span>Reviews submitted</span></div>
  </section>
  <div class="ea-journey-grid">
    <section class="ea-journey-panel">
      <h2>Saved Places</h2>
      {% for entry in saved_preview %}
        <a class="ea-journey-item" href="{% url 'places:place_detail' entry.place.pk %}">{{ entry.place.title }}</a>
      {% empty %}
        <p>Nothing saved yet. Browse places to start your collection.</p>
      {% endfor %}
      <a class="ea-journey-link" href="{% url 'places:saved_places' %}">View Saved Places</a>
    </section>
    <section class="ea-journey-panel">
      <h2>My Itinerary Plans</h2>
      {% for trip in itinerary_preview %}
        <div class="ea-journey-item">{{ trip.title }}{% if trip.day_number %} · Day {{ trip.day_number }}{% endif %}</div>
      {% empty %}
        <p>No Kabankalan itineraries created yet.</p>
      {% endfor %}
      <p class="ea-journey-note">Plan editing will be connected to the existing itinerary builder in the next step.</p>
    </section>
    <section class="ea-journey-panel">
      <h2>My Visits</h2>
      <p>Physical visit tracking is coming in a later phase.</p>
      <p class="ea-journey-note">Viewing a place or requesting directions does not verify a visit.</p>
    </section>
    <section class="ea-journey-panel">
      <h2>Badges and Points</h2>
      <p>Achievements are not active yet. No points or badges will be invented.</p>
      <a class="ea-journey-link" href="{% url 'places:attraction_carousel' %}">Continue Exploring</a>
    </section>
  </div>
</main>
{% endblock %}
'''

CSS_DETAIL = '''
/* ExploreAnywhere phase3 save-and-journey v1 */
.ea-detail-actions {display:flex;align-items:center;flex-wrap:wrap;gap:11px;margin:16px 0 24px}
.ea-detail-actions form {margin:0}
.ea-save-action {background:#075ee4;color:#fff;border:1px solid #075ee4;padding:12px 18px;border-radius:11px;font:inherit;font-weight:750;cursor:pointer}
.ea-save-action.is-saved {color:#0757d8;background:#eaf3ff;border-color:#bad4f6}
.ea-detail-actions a {display:inline-block;padding:12px 15px;border:1px solid #c9d8ec;border-radius:11px;color:#0757d8;text-decoration:none;font-weight:700;background:white}
.ea-save-status {color:#486783;font-size:13px;margin:0}
'''

HTML_DETAIL = '''
    <!-- ExploreAnywhere phase3 save-and-journey v1 -->
    <nav class="ea-detail-actions" aria-label="Place actions">
      {% if is_saved %}
      <form method="post" action="{% url 'places:unsave_place' place.pk %}">
        {% csrf_token %}
        <button type="submit" class="ea-save-action is-saved">Saved ✓ — Remove</button>
      </form>
      {% else %}
      <form method="post" action="{% url 'places:save_place' place.pk %}">
        {% csrf_token %}
        <button type="submit" class="ea-save-action">Save Place</button>
      </form>
      {% endif %}
      <a href="{% url 'places:saved_places' %}">My Saved Places</a>
      <a href="{% url 'places:journey_dashboard' %}">My Journey</a>
    </nav>
'''


def fail(msg):
    raise RuntimeError(msg)


def main():
    for p in [URLS, VIEWS, DETAIL, MODELS]:
        if not (ROOT / p).is_file():
            fail(f"Missing project file: {p}. Run from project root.")
    urls = (ROOT / URLS).read_text(encoding='utf-8-sig')
    views = (ROOT / VIEWS).read_text(encoding='utf-8-sig')
    detail = (ROOT / DETAIL).read_text(encoding='utf-8-sig')
    models = (ROOT / MODELS).read_text(encoding='utf-8-sig')

    if MARKER in urls or MARKER in views or MARKER in detail:
        fail('Phase 3 implementation appears already installed. No files were changed.')
    if 'class SavedPlace(' not in models or 'unique_together = ("user", "place")' not in models:
        fail('SavedPlace schema differs from the audited source. No changes made.')
    if 'def place_detail(request, pk):' not in views:
        fail('Could not find original place_detail view.')
    if 'app_name = "places"' not in urls or 'urlpatterns = [' not in urls:
        fail('places/urls.py differs from the audited structure.')
    if '"places/place_detail.html"' not in views:
        fail('Original detail template reference not found.')
    if '{% block extra_css %}' not in detail or '{% endblock %}' not in detail or '<header class="ea-detail-head">' not in detail:
        fail('Detail template does not match audited structure.')
    for p in (JOURNEY_VIEWS, DASHBOARD):
        if (ROOT / p).exists():
            fail(f'Will not overwrite existing file: {p}')
    if (ROOT / SAVED).exists() and (ROOT / SAVED).stat().st_size > 0:
        fail(f'Will not overwrite non-empty existing file: {SAVED}')

    # Verify that the specific rendering context belongs to place_detail.
    start = views.index('def place_detail(request, pk):')
    end = views.find('\nfrom django.core.paginator import Paginator', start)
    if end < 0:
        end = len(views)
    section = views[start:end]
    target = '            "selected_city": city,\n'
    if section.count(target) != 1:
        fail('Expected unique place detail context anchor not found.')

    changed_views = views[:start] + section.replace(
        target, target + '            "is_saved": SavedPlace.objects.filter(user=request.user, place=place).exists(),\n', 1
    ) + views[end:]
    changed_views = changed_views.replace('from .models import Place\n', 'from .models import Place, SavedPlace\n', 1)
    if 'from .models import Place, SavedPlace\n' not in changed_views:
        fail('Could not safely add SavedPlace import.')
    changed_views += f'\n# {MARKER}\n'

    # Append routes inside urlpatterns; the last route can also be a comment.
    close_index = urls.rfind(']')
    if close_index < 0 or 'urlpatterns = [' not in urls[:close_index]:
        fail('Could not find URL list closing bracket.')
    if 'journey_views' in urls or 'name="saved_places"' in urls:
        fail('Existing Saved/Journey routes need manual review, not automatic overwriting.')
    changed_urls = urls[:close_index] + '''    # ExploreAnywhere phase3 save-and-journey v1
    path("saved/", journey_views.saved_places, name="saved_places"),
    path("journey/", journey_views.journey_dashboard, name="journey_dashboard"),
    path("<int:pk>/save/", journey_views.save_place, name="save_place"),
    path("<int:pk>/unsave/", journey_views.unsave_place, name="unsave_place"),
''' + urls[close_index:]
    changed_urls = changed_urls.replace('from . import views\n', 'from . import views, journey_views\n', 1)
    if 'from . import views, journey_views' not in changed_urls:
        fail('Could not safely add journey_views import.')

    changed_detail = detail.replace('{% endblock %}', CSS_DETAIL + '{% endblock %}', 1)
    changed_detail = changed_detail.replace('    <div class="ea-detail-grid">', HTML_DETAIL + '\n    <div class="ea-detail-grid">', 1)
    if MARKER not in changed_detail:
        fail('Could not insert detail actions.')

    new_content = {
        URLS: changed_urls,
        VIEWS: changed_views,
        DETAIL: changed_detail,
        JOURNEY_VIEWS: NEW_VIEWS,
        SAVED: NEW_SAVED,
        DASHBOARD: NEW_DASHBOARD,
    }
    for p, content in new_content.items():
        if p.suffix == '.py':
            ast.parse(content, filename=str(p))
    if changed_detail.count('{% block extra_css %}') != 1 or changed_detail.count('{% block content %}') != 1:
        fail('Unexpected template blocks; no files changed.')

    backup_dir = ROOT / 'phase3_backups' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup_dir.mkdir(parents=True, exist_ok=False)
    existed = {p: (ROOT / p).exists() for p in new_content}
    for p, exists in existed.items():
        if exists:
            out = backup_dir / p
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / p, out)
    done = []
    try:
        for p, content in new_content.items():
            out = ROOT / p
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(content, encoding='utf-8', newline='\n')
            done.append(p)
    except Exception:
        for p in reversed(done):
            if existed[p]:
                shutil.copy2(backup_dir / p, ROOT / p)
            else:
                (ROOT / p).unlink(missing_ok=True)
        raise
    print('SUCCESS: Phase 3 starter installed.')
    print('Added: POST Save/Unsave, Saved Places, My Kabankalan Journey.')
    print('Preserved: existing DB schema, map, recommendation code, photo data.')
    print('Backup:', backup_dir.relative_to(ROOT))
    print('New routes: /places/saved/ and /places/journey/')
    print('Next: python manage.py check')
    print('Next: python manage.py shell -c "from django.template.loader import get_template; [get_template(x) for x in [\'places/place_detail.html\',\'places/saved_places.html\',\'places/journey_dashboard.html\']]; print(\'Templates OK\')"')

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print('STOPPED:', e, file=sys.stderr)
        sys.exit(1)
