#!/usr/bin/env python3
"""Repair the ExploreAnywhere Kabankalan recommendation template without touching data.

Run from the Django project root:
    python "%USERPROFILE%\\Downloads\\repair_exploreanywhere_places_v2.py"

Creates a timestamped template backup and refuses unexpected template layouts.
"""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

TARGET = Path('templates/places/attraction_carousel.html')
MARKER = 'exploreanywhere-places-repair-v2'


def replace_one(source: str, old: str, new: str, label: str) -> str:
    count = source.count(old)
    if count != 1:
        raise ValueError(f'{label}: expected exactly one anchor, found {count}. No changes made.')
    return source.replace(old, new, 1)


def regex_one(source: str, pattern: str, replacement: str, label: str, flags: int = 0) -> str:
    updated, count = re.subn(pattern, lambda m: replacement, source, count=1, flags=flags)
    if count != 1:
        raise ValueError(f'{label}: expected one matching code block. No changes made.')
    return updated


def repair(source: str) -> str:
    if MARKER in source:
        raise ValueError('This template already contains the v2 repair; no changes made.')
    if '{% for place in attractions %}' not in source or 'const attractions = [];' not in source:
        raise ValueError('Unrecognized attraction template; no changes made.')

    # Remove the misplaced badge before each card (it is currently a loose flex item).
    source = regex_one(
        source,
        r'\{% for place in attractions %\}\s*\{% if place\.match_percent is not None %\}\s*<span class="ea-match-badge">\s*\{\{ place\.match_percent \}\}% (?:Hobby )?Match\s*</span>\s*\{% endif %\}',
        '{% for place in attractions %}',
        'Detached recommendation score badge',
    )

    # This is the source of the all-red/all-zero map bug: JS expects card.dataset.match.
    source = replace_one(
        source,
        'data-detail-url="{% url \'places:place_detail\' place.pk %}"',
        'data-detail-url="{% url \'places:place_detail\' place.pk %}"\n          data-match="{{ place.match_percent|default_if_none:\'0\' }}"',
        'Map recommendation score binding',
    )

    source = replace_one(
        source,
        '<h3>{{ place.title }}</h3>',
        '<h3>{{ place.title }}</h3>\n'
        '              {% if place.match_percent is not None %}\n'
        '              <span class="ea-match-badge" title="Calculated from selected hobbies and available ratings; GPS distance is not included.">\n'
        '                {{ place.match_percent }}% Recommendation Match\n'
        '              </span>\n'
        '              {% endif %}',
        'Move recommendation score into each card',
    )

    # Do not pretend that unrelated stock photography depicts a real Kabankalan attraction.
    source = regex_one(
        source,
        r'\{% else %\}\s*\{% sample_photo place as stock_image %\}\s*<div class="sample-photo-wrapper">.*?</div>\s*\{% endif %\}',
        '{% else %}\n'
        '                <div class="ea-photo-empty" role="img" aria-label="No verified photo available for {{ place.title }}">\n'
        '                  <span class="ea-photo-empty-icon" aria-hidden="true">&#128247;</span>\n'
        '                  <span>Destination photo coming soon</span>\n'
        '                </div>\n'
        '              {% endif %}',
        'Replace stock photo fallback only',
        flags=re.S,
    )

    # Use place-specific navigation, but keep existing external map links unchanged.
    source = replace_one(source, '&#8592; Change City', '&#8592; Change Hobbies', 'Header label')
    source = replace_one(source, 'Choose Another City', 'Change Hobbies', 'Empty-state label')
    source = replace_one(
        source,
        'Try another search or choose a different city.',
        'Try another search or adjust your selected hobbies.',
        'Empty-state guidance',
    )
    source = replace_one(
        source,
        'Explore approved destinations and attractions\n        in your selected city or municipality.',
        'Explore verified destinations and attractions\n        in Kabankalan City, Negros Occidental.',
        'City-specific subtitle',
    )

    # Explicit notes to avoid suggesting the 60/20/20 GPS component is operating.
    source = replace_one(
        source,
        '<div id="ea-list-panel">',
        '<p class="ea-match-explainer">Recommendation scores use your selected hobbies and available ratings. '
        'GPS distance is not included yet.</p>\n\n<div id="ea-list-panel">',
        'Matching score explanation',
    )

    # Clean up labels in JavaScript irrespective of how the old arrow was mojibaked.
    source = regex_one(
        source,
        r'^\s*directions\.textContent\s*=\s*"[^"\r\n]*";',
        '        directions.textContent = "Get Directions";',
        'Directions button label',
        flags=re.M,
    )
    source = regex_one(
        source,
        r'^\s*detailLink\.textContent\s*=\s*"[^"\r\n]*";',
        '        detailLink.textContent = "View Full Details";',
        'Full details button label',
        flags=re.M,
    )
    source = replace_one(
        source,
        '            coordinates,\n            directions\n        );',
        '            coordinates,\n            directions,\n            detailLink\n        );',
        'Display full details link in the map sidebar',
    )
    source = replace_one(
        source,
        '            const detailLink = document.createElement("a");',
        '        const detailLink = document.createElement("a");',
        'Map details link alignment',
    )
    source = regex_one(
        source,
        r'^detailLink\.className = ',
        '        detailLink.className = ',
        'Details class alignment', flags=re.M,
    )
    source = regex_one(
        source,
        r'^detailLink\.href = ',
        '        detailLink.href = ',
        'Details href alignment', flags=re.M,
    )

    # The current labels say Hobby Match, but ranking also uses available ratings.
    source = replace_one(source, 'const hobbyLegend = L.control(', 'const hobbyLegend = L.control(', 'Map legend presence')
    source = replace_one(source, '"Hobby match marker legend"', '"Recommendation match marker legend"', 'Legend aria label')
    source = replace_one(source, "'<strong>Hobby match</strong>", "'<strong>Recommendation match</strong>", 'Legend heading')
    source = replace_one(source, '"% Hobby Match";', '"% Recommendation Match";', 'Popup score label')

    styles = r'''
/* exploreanywhere-places-repair-v2: fixes card overflow and keeps the original carousel/map. */
.ea-attractions { max-width: 1280px; }
.ea-carousel { gap: 16px; padding-bottom: 18px; }
.ea-carousel .ea-card {
  flex: 0 0 clamp(260px, 30%, 340px);
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.ea-card-body { display: flex; flex-direction: column; flex: 1; padding: 20px; min-width: 0; }
.ea-card-image { height: 180px; }
.ea-card .ea-match-badge {
  align-self: flex-start;
  margin: 0 0 12px;
  white-space: normal;
  line-height: 1.35;
}
.ea-card-description { min-height: 0; }
.ea-card-footer {
  margin-top: auto;
  padding-top: 16px;
  display: flex;
  gap: 10px 14px;
  flex-wrap: wrap;
  align-items: center;
}
.ea-card-footer .ea-map-link {
  display: inline-flex !important;
  align-items: center;
  margin-bottom: 0 !important;
  min-height: 38px;
}
.ea-photo-empty {
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
  gap: 9px; padding: 18px;
  color: #315f85; background: linear-gradient(145deg, #e8f3ff, #e9f7f1);
  text-align: center; font-size: 12px; font-weight: 700;
}
.ea-photo-empty-icon { font-size: 32px; line-height: 1; }
.ea-match-explainer {
  margin: 0 0 14px; color: #526781; font-size: 12px; line-height: 1.5;
}
.ea-map-details .ea-detail-button + .ea-detail-button {
  color: #075ee4 !important; background: #eef5ff;
  border: 1px solid #cde1ff;
}
.ea-map-details .ea-detail-button + .ea-detail-button:hover { background: #dceaff; }
@media (max-width: 700px) {
  .ea-carousel .ea-card { flex: 0 0 min(86vw, 330px); }
  .ea-card-image { height: 160px; }
  .ea-map-layout { grid-template-columns: 1fr; }
}
'''
    # Insert CSS just before the first style close, not inside the content-style block.
    source = replace_one(source, '</style>\n{% endblock %}', styles + '\n</style>\n{% endblock %}', 'Styles placement')

    assert source.count(MARKER) == 1
    assert 'data-match="{{ place.match_percent|default_if_none:' in source
    assert '            detailLink\n        );' in source
    return source


def main() -> int:
    if not TARGET.is_file():
        print('ERROR: Cannot find templates/places/attraction_carousel.html')
        print('Open your ExploreAnywhere project folder in PowerShell and run the command there.')
        return 1
    raw = TARGET.read_bytes()
    line_ending = '\r\n' if b'\r\n' in raw else '\n'
    try:
        source = raw.decode('utf-8-sig').replace('\r\n', '\n')
        result = repair(source)
    except (ValueError, UnicodeError) as exc:
        print('ERROR:', exc)
        return 1

    suffix = datetime.now().strftime('%Y%m%d-%H%M%S')
    backup = TARGET.with_name(f'{TARGET.name}.pre-places-v2-{suffix}.bak')
    if backup.exists():
        print('ERROR: Backup path already exists; please retry.')
        return 1
    shutil.copy2(TARGET, backup)
    try:
        TARGET.write_bytes(result.replace('\n', line_ending).encode('utf-8'))
    except Exception:
        shutil.copy2(backup, TARGET)
        raise

    print('SUCCESS: Recommendation template repaired.')
    print('Fixed missing map data-match, card badges, card layout, photo fallback, labels, and map details link.')
    print('Backup:', backup)
    print('No Django models, database content, or MapTiler key were modified.')
    print('Next: python manage.py shell -c "from django.template.loader import get_template; get_template(\'places/attraction_carousel.html\'); print(\'Template OK\')"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
