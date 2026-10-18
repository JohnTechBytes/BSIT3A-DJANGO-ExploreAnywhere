#!/usr/bin/env python3
"""Read-only Phase 4 UI/UX audit for ExploreAnywhere: Kabankalan City Edition.
Run from the project root: python "%USERPROFILE%\\Downloads\\exploreanywhere_phase4_ui_audit.py"
No files, migrations, or database records are modified.
"""
from pathlib import Path
import os
import re
import sys

ROOT = Path.cwd()
if not (ROOT / 'manage.py').is_file() or not (ROOT / 'mysite' / 'settings.py').is_file():
    sys.exit('ERROR: Open PowerShell in your ExploreAnywhere Django project folder before running this script.')
sys.path.insert(0, str(ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')


def heading(title):
    print('\n' + '=' * 68 + '\n' + title + '\n' + '=' * 68)


print('ExploreAnywhere — PHASE 4 UI/UX READ-ONLY AUDIT')
print('Project:', ROOT)
print('This tool only reads project source and resolves URLs. It makes NO changes.')

try:
    import django
    django.setup()
    from django.template.loader import get_template
    from django.urls import resolve, Resolver404
except Exception as exc:
    sys.exit(f'Django initialization failed: {type(exc).__name__}: {exc}')

heading('1. USER JOURNEY ROUTES (routing only; NOT browser authentication tests)')
paths = [
    ('Homepage', '/'),
    ('Hobby Selection', '/hobbies/'),
    ('Natural-Language Search', '/hobbies/search/'),
    ('Recommendations', '/places/'),
    ('Place Details', '/places/1702/'),
    ('Saved Places', '/places/saved/'),
    ('My Kabankalan Journey', '/places/journey/'),
    ('My Reviews', '/places/my-reviews/'),
    ('Itineraries', '/itineraries/'),
    ('Create Itinerary', '/itineraries/new/'),
    ('My Visits', '/visits/'),
    ('Report Visit', '/visits/check-in/1702/'),
    ('Old city selection', '/cities/select/'),
]
for label, path in paths:
    try:
        match = resolve(path)
        print(f'OK   {label:24} {path:31} -> {match.view_name or "(unnamed)"}')
    except Resolver404:
        print(f'MISSING {label:21} {path}')
    except Exception as exc:
        print(f'ERROR {label:23} {path}: {type(exc).__name__}: {exc}')

heading('2. TEMPLATE COMPILATION (structure only; NOT browser render tests)')
templates = [
    'home.html',
    'theme/public_base.html',
    'hobbies/hobby_selection.html',
    'places/attraction_carousel.html',
    'places/place_detail.html',
    'places/saved_places.html',
    'places/journey_dashboard.html',
    'places/my_reviews.html',
    'itineraries/create.html',
    'itineraries/builder.html',
    'itineraries/my_itineraries.html',
    'visits/check_in.html',
    'visits/my_visits.html',
]
for template in templates:
    try:
        get_template(template)
        print('OK     ', template)
    except Exception as exc:
        print('ISSUE  ', template, '->', type(exc).__name__, str(exc)[:180])

heading('3. NAVIGATION & OUTDATED MULTI-CITY LANGUAGE')
needles = ['Explore Cities', 'Change City', 'Choose Another City', 'Choose a City', 'Select Province']
found = 0
for path in sorted((ROOT / 'templates').rglob('*.html')):
    if any(token in path.name for token in ('.bak', '.backup', '.old')):
        continue
    try:
        content = path.read_text(encoding='utf-8-sig')
    except (UnicodeError, OSError):
        continue
    for number, line in enumerate(content.splitlines(), 1):
        if any(needle.lower() in line.lower() for needle in needles):
            found += 1
            if found <= 35:
                rel = path.relative_to(ROOT)
                print(f'{rel}:{number}: {line.strip()[:150]}')
print('Total old/multi-city text hits:', found)
if not found:
    print('None found in local HTML templates.')

heading('4. LAYOUT, MOBILE & ACCESSIBILITY QUICK SIGNALS')
for t in ['theme/public_base.html','home.html','places/journey_dashboard.html',
          'places/saved_places.html','places/attraction_carousel.html',
          'places/place_detail.html','itineraries/builder.html','visits/my_visits.html']:
    path = ROOT / 'templates' / t
    if not path.is_file():
        print('MISSING FILE', t)
        continue
    try:
        src = path.read_text(encoding='utf-8-sig')
    except (UnicodeError, OSError):
        print('UNREADABLE ', t)
        continue
    mobile = bool(re.search(r'@media\s*\(', src, re.IGNORECASE))
    controls = bool(re.search(r'<(button|form|input|select)\b', src, re.IGNORECASE))
    viewport = bool(re.search(r'name\s*=\s*[\"\']viewport[\"\']', src, re.IGNORECASE))
    print(f'{t:40} media_query={"yes" if mobile else "no"} interactive_controls={"yes" if controls else "no"} viewport_meta={"yes" if viewport else "inherits/none"}')
print('Note: These are signals, not a WCAG/mobile compliance score. Test in browser.')

heading('5. WHERE YOUR SHARED NAVIGATION LIVES')
for t in ['theme/public_base.html','home.html']:
    path = ROOT / 'templates' / t
    if path.exists():
        content = path.read_text(encoding='utf-8-sig', errors='replace')
        print(f'{t}: {len(content.splitlines())} lines; navbar references={len(re.findall(r"navbar|<nav\\b", content, re.I))}')

heading('NEXT STEP')
print('Paste this output into ChatGPT. We will fix the shared navbar and mobile layout first.')
print('Do not run migrations: Phase 4 UI polish should not require schema changes.')
