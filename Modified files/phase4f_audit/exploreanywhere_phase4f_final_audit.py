#!/usr/bin/env python3
"""ExploreAnywhere Phase 4F: read-only release-readiness audit.

Run from the Django project root:
  python path/to/exploreanywhere_phase4f_final_audit.py

Does not modify code, database rows, migrations, sessions, users, or files.
It does NOT replace manual authentication, CSRF, permissions, or browser testing.
"""
from __future__ import annotations

import ast
import os
from pathlib import Path
import sys

ROOT = Path.cwd()
if not (ROOT / 'manage.py').is_file() or not (ROOT / 'mysite' / 'settings.py').is_file():
    sys.exit('ERROR: Run this from the ExploreAnywhere folder containing manage.py.')
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')

passes = []
issues = []
warnings = []


def record(label, ok, info='', *, warning=False):
    state = 'PASS' if ok else ('NOTE' if warning else 'FAIL')
    print(f'{state:4} {label}' + (f' — {info}' if info else ''))
    if ok:
        passes.append(label)
    elif warning:
        warnings.append(label + (': ' + info if info else ''))
    else:
        issues.append(label + (': ' + info if info else ''))


def section(label):
    print('\n' + '=' * 67)
    print(label)
    print('=' * 67)


print('EXPLOREANYWHERE — PHASE 4F FINAL READ-ONLY AUDIT')
print('Project:', ROOT)
print('No project files, database records, sessions, or migrations will be changed.')

try:
    import django
    django.setup()
    from django.apps import apps
    from django.conf import settings
    from django.core.checks import run_checks, ERROR
    from django.db import connection
    from django.db.migrations.executor import MigrationExecutor
    from django.template.loader import get_template
    from django.urls import Resolver404, resolve
    from django.db.models import Avg
except Exception as exc:
    sys.exit(f'ERROR: Django initialization failed: {type(exc).__name__}: {exc}')

section('1. DJANGO & MIGRATIONS')
try:
    error_checks = [check for check in run_checks() if check.is_serious(ERROR)]
    record('Django system checks', not error_checks,
           ', '.join(str(e)[:120] for e in error_checks[:3]) if error_checks else 'no errors')
except Exception as exc:
    record('Django system checks', False, f'{type(exc).__name__}: {exc}')

try:
    executor = MigrationExecutor(connection)
    targets = executor.loader.graph.leaf_nodes()
    plan = executor.migration_plan(targets)
    pending = [f'{migration.app_label}.{migration.name}' for migration, backwards in plan if not backwards]
    record('Applied migration state', not pending,
           f'pending: {", ".join(pending[:8])}' if pending else 'all migration leaf nodes applied')
except Exception as exc:
    record('Applied migration state', False, f'{type(exc).__name__}: {exc}')

section('2. USER JOURNEY ROUTES')
paths = [
    ('Homepage', '/', 'home'),
    ('Hobby Selection', '/hobbies/', 'hobbies:select'),
    ('Hobby Search', '/hobbies/search/', 'hobbies:search'),
    ('Browse Kabankalan', '/places/', 'places:attraction_carousel'),
    ('Place Details', '/places/1702/', 'places:place_detail'),
    ('Saved Places', '/places/saved/', 'places:saved_places'),
    ('My Journey', '/places/journey/', 'places:journey_dashboard'),
    ('My Reviews', '/places/my-reviews/', 'places:my_reviews'),
    ('Itineraries', '/itineraries/', 'itineraries:list'),
    ('Create Itinerary', '/itineraries/new/', 'itineraries:create'),
    ('Itinerary Chooser', '/itineraries/add-place/1702/', None),
    ('My Visits', '/visits/', 'visits:list'),
    ('Report Visit', '/visits/check-in/1702/', 'visits:check_in'),
]
for label, path, expected in paths:
    try:
        actual = resolve(path).view_name
        record(label, actual == expected if expected else bool(actual), f'{path} → {actual}')
    except Resolver404:
        record(label, False, f'{path} not found')
    except Exception as exc:
        record(label, False, f'{type(exc).__name__}: {exc}')

section('3. PAGE TEMPLATES')
templates = [
    'home.html', 'theme/public_base.html', 'hobbies/hobby_selection.html',
    'places/attraction_carousel.html', 'places/place_detail.html',
    'places/saved_places.html', 'places/journey_dashboard.html',
    'places/my_reviews.html', 'itineraries/create.html',
    'itineraries/builder.html', 'itineraries/my_itineraries.html',
    'itineraries/choose_for_place.html', 'visits/check_in.html',
    'visits/my_visits.html',
]
for item in templates:
    try:
        get_template(item)
        record(item, True)
    except Exception as exc:
        record(item, False, f'{type(exc).__name__}: {str(exc)[:130]}')

section('4. EXPLORE PLACES DIRECT NAVIGATION (STATIC GUARDS)')
view_path = ROOT / 'apps' / 'places' / 'views.py'
try:
    src = view_path.read_text(encoding='utf-8-sig')
    tree = ast.parse(src)
    funcs = {node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
    carousel = ast.get_source_segment(src, funcs['attraction_carousel'])
    details = ast.get_source_segment(src, funcs['place_detail'])
    record('Browse-all resets old search',
           'request.GET.get("browse") == "all"' in carousel and 'attraction_search_query' in carousel)
    record('Browse does not force hobby selection',
           'redirect("hobbies:select")' not in carousel and "redirect('hobbies:select')" not in carousel)
    record('Details do not force hobby selection',
           'redirect("hobbies:select")' not in details and "redirect('hobbies:select')" not in details)
    record('Published and Kabankalan filtering in browse',
           all(s in carousel for s in ('is_active=True', 'is_verified=True', 'city=city')))
except Exception as exc:
    record('Explore/Details source inspection', False, f'{type(exc).__name__}: {exc}')

for item in ('templates/home.html', 'templates/theme/public_base.html'):
    try:
        src = (ROOT / item).read_text(encoding='utf-8-sig')
        record(f'Explore link in {Path(item).name}',
               "{% url 'places:attraction_carousel' %}?browse=all" in src,
               'expected destination /places/?browse=all')
    except Exception as exc:
        record(f'Explore link in {Path(item).name}', False, f'{type(exc).__name__}: {exc}')

section('5. KABANKALAN DESTINATION DATA QUALITY')
try:
    City = apps.get_model('cities', 'City')
    Place = apps.get_model('places', 'Place')
    Review = apps.get_model('places', 'Review')
    city = City.objects.filter(pk=2).values('name', 'province').first()
    record('Kabankalan city identity', bool(city and city['name'].casefold() == 'kabankalan'),
           f'name={city["name"] if city else "missing"}')
    places = list(Place.objects.filter(city_id=2, is_active=True, is_verified=True)
                  .prefetch_related('hobbies').order_by('title'))
    record('Published Kabankalan destination count', len(places) == 7,
           str(len(places)) + ' (expected 7 based on last audit)')
    missing_photo = []
    missing_description = []
    missing_coordinates = []
    missing_hobbies = []
    mismatched_ratings = []
    for p in places:
        if not bool(p.cover_image) and not bool((p.cover_image_url or '').strip()):
            missing_photo.append(p.title)
        if not (p.description or '').strip():
            missing_description.append(p.title)
        if p.latitude is None or p.longitude is None:
            missing_coordinates.append(p.title)
        if not p.hobbies.exists():
            missing_hobbies.append(p.title)
        stats = Review.objects.filter(place_id=p.pk).aggregate(avg=Avg('rating'))
        actual_count = Review.objects.filter(place_id=p.pk).count()
        actual_avg = float(stats['avg'] or 0)
        recorded_avg = float(p.avg_rating or 0)
        if actual_count != p.review_count or (actual_count and abs(recorded_avg - actual_avg) > 0.011):
            mismatched_ratings.append(p.title)
    record('Review aggregate consistency', not mismatched_ratings,
           'all matches' if not mismatched_ratings else ', '.join(mismatched_ratings))
    record('Photo metadata', not missing_photo,
           f'{len(missing_photo)} destination(s) missing genuine cover image metadata: '+', '.join(missing_photo), warning=True)
    record('Descriptions', not missing_description,
           f'{len(missing_description)} destination(s) missing: '+', '.join(missing_description), warning=True)
    record('Coordinates', not missing_coordinates,
           f'{len(missing_coordinates)} destination(s) missing: '+', '.join(missing_coordinates), warning=True)
    record('Hobby assignments', not missing_hobbies,
           f'{len(missing_hobbies)} destination(s) missing: '+', '.join(missing_hobbies), warning=True)
except Exception as exc:
    record('Destination data quality inspection', False, f'{type(exc).__name__}: {exc}')

section('6. RELEASE SAFETY NOTES')
record('Production DEBUG setting', not bool(settings.DEBUG),
       'DEBUG=True: acceptable for local development, NOT for public deployment', warning=True)
record('Allowed hosts setting', bool(settings.ALLOWED_HOSTS),
       'ALLOWED_HOSTS empty; configure deployment hosts before public release', warning=True)
print('MANUAL TEST REQUIRED: anonymous login redirects, session expiry, CSRF rejection,')
print('cross-account isolation, staff-only approvals, duplicate saves and visits,')
print('mobile navigation, map interaction, uploaded media licensing and photo validity.')
print('No HTTP requests were sent and no database or source data was changed.')

section('SUMMARY')
print('PASS:', len(passes), '| FAIL:', len(issues), '| NOTES:', len(warnings))
if issues:
    print('Failures to investigate:')
    for item in issues[:20]:
        print(' -', item)
if warnings:
    print('Outstanding release notes:')
    for item in warnings[:20]:
        print(' -', item)
print('\nDONE: Paste the audit result into ChatGPT. Do not confuse a static check with browser or security penetration testing.')
