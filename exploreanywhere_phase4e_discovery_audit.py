#!/usr/bin/env python3
"""Read-only Phase 4E audit for ExploreAnywhere: Kabankalan City Edition.

Run from the Django project directory with its virtual environment active.
Does not print API keys, database credentials, user details, or photo URLs.
"""
from pathlib import Path
import os
import re
import sys

ROOT = Path.cwd()


def section(title):
    print('\n' + '=' * 68)
    print(title)
    print('=' * 68)


def flag(ok):
    return 'OK  ' if ok else 'CHECK'


def read_template(relative):
    path = ROOT / relative
    if not path.is_file():
        print(f'CHECK Missing template: {relative}')
        return None
    try:
        return path.read_text(encoding='utf-8-sig')
    except Exception as exc:
        print(f'CHECK Cannot read {relative}: {exc.__class__.__name__}')
        return None


def check(condition, label):
    print(f'{flag(bool(condition))} {label}')


def run():
    print('ExploreAnywhere - PHASE 4E DISCOVERY READ-ONLY AUDIT')
    print(f'Project: {ROOT}')
    print('No source files, photos, database records or migrations will be modified.')
    print('No external requests will be made; no secrets or user accounts are printed.')
    if not (ROOT / 'manage.py').is_file():
        print('\nERROR: Run this script from the folder containing manage.py.')
        return 2

    section('1. PROJECT & DJANGO')
    sys.path.insert(0, str(ROOT))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings')
    try:
        import django
        django.setup()
        print(f'OK   Django {django.get_version()} initialized')
    except Exception as exc:
        print(f'CHECK Django could not initialize: {type(exc).__name__}: {exc}')
        print('Tip: confirm that the project virtual environment is active.')
        return 1

    section('2. PUBLISHED KABANKALAN DESTINATION QUALITY')
    try:
        from apps.places.models import Place, PlacePhoto
        queryset = Place.objects.filter(city_id=2, is_active=True, is_verified=True).order_by('title')
        places = list(queryset)
        place_ids = [p.pk for p in places]
        photo_map = set()
        if place_ids:
            for photo in PlacePhoto.objects.filter(place_id__in=place_ids).only('place_id', 'image', 'image_url'):
                if bool(photo.image) or bool(photo.image_url):
                    photo_map.add(photo.place_id)
        print(f'Published, verified Kabankalan destinations: {len(places)}')
        print('Coverage: genuine image attached/URL field; external image validity is not verified.')
        genuine_count = description_count = coords_count = rated_count = 0
        for place in places:
            genuine = bool(place.cover_image) or bool(place.cover_image_url) or place.pk in photo_map
            desc = bool((place.description or '').strip())
            coords = place.latitude is not None and place.longitude is not None
            rated = bool(place.review_count and place.avg_rating)
            genuine_count += genuine
            description_count += desc
            coords_count += coords
            rated_count += rated
            name = str(place.title).replace('\n', ' ')[:62]
            print(f'  {name}: photo={"yes" if genuine else "missing"}, description={"yes" if desc else "missing"}, coordinates={"yes" if coords else "missing"}')
        print(f'Photo metadata coverage: {genuine_count}/{len(places)}')
        print(f'Description coverage:    {description_count}/{len(places)}')
        print(f'Coordinate coverage:     {coords_count}/{len(places)}')
        print(f'Places with ratings:     {rated_count}/{len(places)}')
        if not places:
            print('CHECK No published Kabankalan places were returned; check database availability.')
    except Exception as exc:
        print(f'CHECK Unable to inspect destinations: {type(exc).__name__}: {exc}')
        print('Verify MySQL in XAMPP is running and Django database settings are correct.')

    section('3. RECOMMENDATIONS TEMPLATE & LEAFLET MAP')
    target = read_template('templates/places/attraction_carousel.html')
    if target is not None:
        checks = [
            (bool(re.search(r'data-match\s*=', target)), 'Match score provided in card data-match'),
            ('data-lat' in target and 'data-lng' in target, 'Destination coordinates provided to map'),
            ('leaflet' in target.lower(), 'Leaflet map references present'),
            ('ea-map-button' in target and 'ea-list-button' in target, 'Map/List toggle controls present'),
            ('matchPercent' in target, 'Recommendation score used by map'),
            ('legend' in target.lower(), 'Map legend present'),
            ('fitBounds' in target, 'Automatic map marker bounds'),
            ('attraction.card.dataset.detailUrl' in target or 'data-detail-url' in target, 'Destination detail route in cards'),
            ('https://www.google.com/maps/' in target, 'External Google Maps navigation'),
            ('no destination photo' in target.lower() or 'photo coming soon' in target.lower() or 'ea-placeholder' in target, 'Photo placeholder/fallback present'),
        ]
        for is_ok, label in checks:
            check(is_ok, label)
        for label, matcher in [
            ('Unresolved mojibake markers (common patterns)', r'(?:Ã¢|â€|Â¢|Ã—|ï¿½)'),
            ('Potential hardcoded sample-photo helper', r'\bsample_photo\b'),
        ]:
            hits = len(re.findall(matcher, target))
            print(f'{"CHECK" if hits else "OK   "} {label}: {hits}')
        check('{% for place in attractions %}' in target, 'Cards rendered from actual Django results')

    section('4. DISCOVERY SEARCH & HOBBIES')
    files = {
        'templates/hobbies/hobby_selection.html': 'Hobby selection UI',
        'apps/hobbies/views.py': 'Hobby and search handlers',
        'apps/places/recommendations.py': 'Recommendation ranking',
        'apps/places/views.py': 'Places views',
        'templates/places/place_detail.html': 'Destination details',
    }
    for rel, label in files.items():
        path = ROOT / rel
        check(path.is_file(), f'{label}: {rel}')
    hobbies_views = read_template('apps/hobbies/views.py')
    if hobbies_views is not None:
        check('hobbies_city_id' in hobbies_views or 'selected_hobbies' in hobbies_views, 'Selected hobbies tracked'),
        check('Kabankalan' in hobbies_views or 'city_id=2' in hobbies_views or 'pk=2' in hobbies_views, 'Kabankalan city restriction appears in search views')
    ranking = read_template('apps/places/recommendations.py')
    if ranking is not None:
        check('rank_kabankalan_places' in ranking, 'Kabankalan ranking function present')
        check('review_count' in ranking, 'Rating availability considered in ranking')
        print('NOTE Scoring correctness must be checked with selected-hobby test cases.')

    section('5. RECOMMENDED NEXT WORK')
    print('A. Add correctly attributed photos only where genuine source media exists.')
    print('B. Verify recommendation score labels for hobby-only and rating-supported cases.')
    print('C. Test no-results searches, missing coordinates, and mobile map controls.')
    print('D. Test map/list switching, popup -> details -> save -> itinerary journey.')
    print('E. Leave MapTiler keys, views, models, and migrations untouched until changes are reviewed.')
    print('\nDONE: Read-only audit complete. Paste this output into ChatGPT.')
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
