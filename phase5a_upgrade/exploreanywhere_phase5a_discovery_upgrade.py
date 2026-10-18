#!/usr/bin/env python3
"""ExploreAnywhere Phase 5A: optional direct Explore Places filters + sort.

Run from the ExploreAnywhere project root:
    python exploreanywhere_phase5a_discovery_upgrade.py --dry-run
    python exploreanywhere_phase5a_discovery_upgrade.py

Only changes apps/places/views.py and templates/places/attraction_carousel.html.
Automatic dated backups, exact-anchor protections, and no database actions.
"""

from __future__ import annotations

import argparse
import ast
from datetime import datetime
from pathlib import Path
import sys

MARKER = "exploreanywhere-phase5a-discovery-controls-v1"


def exactly_once(text: str, old: str, new: str, description: str) -> str:
    n = text.count(old)
    if n != 1:
        raise ValueError(f"{description}: expected 1 matching anchor, found {n}. No changes applied.")
    return text.replace(old, new, 1)


def build_view(original: str) -> str:
    prior_block = '''    # The navbar Explore Places link resets only the previous text search.
    # Keep chosen hobbies so a visitor can still see personalized scores.
    if request.GET.get("browse") == "all":
        request.session.pop("attraction_search_query", None)

    search_query = (
        request.session.get("attraction_search_query") or ""
    ).strip()

    attractions = (
        Place.objects.filter(
            city=city,
            is_active=True,
            is_verified=True,
        )
        .select_related("city", "category")
    )

'''
    new_block = '''    # exploreanywhere-phase5a-discovery-controls-v1
    # Browse all resets the previous search; hobby personalization is preserved.
    browse_all = request.GET.get("browse") == "all"
    if browse_all:
        request.session.pop("attraction_search_query", None)
        search_query = ""
    elif "q" in request.GET:
        # Inline search shares the existing hobby-search session convention.
        search_query = (request.GET.get("q") or "").strip()[:200]
        if search_query:
            request.session["attraction_search_query"] = search_query
        else:
            request.session.pop("attraction_search_query", None)
    else:
        search_query = (
            request.session.get("attraction_search_query") or ""
        ).strip()[:200]

    # Only offer category/hobby filters used by published Kabankalan places.
    published_places = (
        Place.objects.filter(city=city, is_active=True, is_verified=True)
        .select_related("city", "category")
    )
    available_categories = {}
    available_hobbies = {}
    published_total = 0
    for published_place in published_places.prefetch_related("hobbies"):
        published_total += 1
        if published_place.category_id and published_place.category:
            available_categories[str(published_place.category_id)] = str(published_place.category)
        for hobby in published_place.hobbies.all():
            if hobby.slug:
                available_hobbies[hobby.slug] = str(hobby)

    category_options = sorted(
        ({"value": key, "label": value} for key, value in available_categories.items()),
        key=lambda item: item["label"].casefold(),
    )
    hobby_options = sorted(
        ({"value": key, "label": value} for key, value in available_hobbies.items()),
        key=lambda item: item["label"].casefold(),
    )

    selected_category = "" if browse_all else (request.GET.get("category") or "").strip()
    selected_hobby = "" if browse_all else (request.GET.get("hobby") or "").strip()
    selected_sort = "recommended" if browse_all else (request.GET.get("sort") or "recommended")
    if selected_category not in available_categories:
        selected_category = ""
    if selected_hobby not in available_hobbies:
        selected_hobby = ""
    if selected_sort not in {"recommended", "rating", "name"}:
        selected_sort = "recommended"

    attractions = published_places
    if selected_category:
        attractions = attractions.filter(category_id=int(selected_category))
    if selected_hobby:
        attractions = attractions.filter(hobbies__slug=selected_hobby).distinct()

'''
    updated = exactly_once(original, prior_block, new_block, "Browse/search block")

    prior_sort = '''    attractions = rank_kabankalan_places(
        attractions.prefetch_related("hobbies"),
        request.session.get("selected_hobbies", []),
    )

    paginator = Paginator(attractions, 12)
'''
    new_sort = '''    attractions = rank_kabankalan_places(
        attractions.prefetch_related("hobbies"),
        request.session.get("selected_hobbies", []),
    )

    # Sorting affects display only; preserve existing recommendation scores.
    if selected_sort == "name":
        attractions.sort(key=lambda place: (place.title or "").casefold())
    elif selected_sort == "rating":
        attractions.sort(key=lambda place: (
            -float(place.avg_rating or 0),
            -int(place.review_count or 0),
            (place.title or "").casefold(),
        ))

    paginator = Paginator(attractions, 12)
'''
    updated = exactly_once(updated, prior_sort, new_sort, "Recommendation/display sort")

    updated = exactly_once(
        updated,
        '            "search_query": search_query,\n',
        '''            "search_query": search_query,
            "published_total": published_total,
            "category_options": category_options,
            "hobby_options": hobby_options,
            "selected_category": selected_category,
            "selected_hobby": selected_hobby,
            "selected_sort": selected_sort,
''',
        "Template filter context",
    )
    # A syntax check catches broken view patches even without Django installed.
    ast.parse(updated)
    return updated


FILTER_STYLE = '''
/* exploreanywhere-phase5a-discovery-controls-v1: mobile-first filter tools */
.ea-discovery-tools {
  padding: 20px; margin: 0 0 26px; background: #fff;
  border: 1px solid #dbe6f4; border-radius: 20px;
  box-shadow: 0 12px 32px rgba(16,43,83,.055);
}
.ea-tools-heading {display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:17px; flex-wrap:wrap;}
.ea-tools-heading h2 {font-size:19px; font-weight:800; color:#102b53; margin:0 0 3px;}
.ea-tools-heading p {font-size:13px; color:#64748b; margin:0; line-height:1.5;}
.ea-tools-form {display:grid; grid-template-columns:minmax(210px,2fr) repeat(3,minmax(130px,1fr)); gap:14px; align-items:end;}
.ea-tool-field {display:flex; flex-direction:column; gap:7px; min-width:0;}
.ea-tool-field label {font-size:12px; font-weight:800; color:#1e3d66;}
.ea-tool-field input, .ea-tool-field select {
  display:block; width:100%; min-height:46px; padding:10px 12px;
  border-radius:11px; border:1px solid #cbd9eb; background:#fff;
  color:#193656; font:inherit; font-size:14px;
}
.ea-tool-field input:focus-visible, .ea-tool-field select:focus-visible,
.ea-tools-actions a:focus-visible, .ea-tools-actions button:focus-visible {
  outline:3px solid #82b5ff; outline-offset:2px;
}
.ea-tools-actions {display:flex; align-items:center; gap:11px; flex-wrap:wrap; margin-top:16px;}
.ea-tools-actions button {background:#0757d8; border:1px solid #0757d8; color:#fff; border-radius:11px; min-height:44px; padding:10px 18px; font:inherit; font-size:13px; font-weight:800; cursor:pointer;}
.ea-tools-actions button:hover {background:#064ab3;}
.ea-tools-actions a {text-decoration:none; border:1px solid #ccd9eb; border-radius:11px; min-height:44px; padding:10px 16px; color:#164476; display:inline-flex; align-items:center; font-size:13px; font-weight:700;}
.ea-tools-actions a:hover {background:#eff6ff;}
.ea-tools-feedback {font-size:13px; color:#536a87; line-height:1.5; margin:0 0 18px;}
.ea-discovery-count {font-size:12px; color:#456484; font-weight:700; white-space:nowrap;}
@media(max-width:1000px) {.ea-tools-form {grid-template-columns:repeat(2,minmax(0,1fr));}}
@media(max-width:560px) {
  .ea-discovery-tools {padding:16px; border-radius:16px;}
  .ea-tools-form {grid-template-columns:minmax(0,1fr); gap:12px;}
  .ea-tools-actions button, .ea-tools-actions a {flex:1; justify-content:center;}
}
'''

FILTER_HTML = '''
  {# exploreanywhere-phase5a-discovery-controls-v1 #}
  <section class="ea-discovery-tools" aria-label="Find and filter Kabankalan destinations">
    <div class="ea-tools-heading">
      <div>
        <h2>Find your next stop</h2>
        <p>Search and filter verified Kabankalan destinations.</p>
      </div>
      <span class="ea-discovery-count">{{ total_attractions }} of {{ published_total }} published</span>
    </div>
    <form class="ea-tools-form" method="get" action="{% url 'places:attraction_carousel' %}" role="search">
      <div class="ea-tool-field">
        <label for="ea-search-query">Destination or activity</label>
        <input id="ea-search-query" name="q" type="search" maxlength="200"
               value="{{ search_query }}" placeholder="e.g. Amyan Hill, waterfalls" autocomplete="off">
      </div>
      <div class="ea-tool-field">
        <label for="ea-filter-category">Category</label>
        <select id="ea-filter-category" name="category">
          <option value="">All categories</option>
          {% for option in category_options %}
            <option value="{{ option.value }}" {% if selected_category == option.value %}selected{% endif %}>{{ option.label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="ea-tool-field">
        <label for="ea-filter-hobby">Explore by hobby</label>
        <select id="ea-filter-hobby" name="hobby">
          <option value="">All hobbies</option>
          {% for option in hobby_options %}
            <option value="{{ option.value }}" {% if selected_hobby == option.value %}selected{% endif %}>{{ option.label }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="ea-tool-field">
        <label for="ea-filter-sort">Sort destinations</label>
        <select id="ea-filter-sort" name="sort">
          <option value="recommended" {% if selected_sort == 'recommended' %}selected{% endif %}>Recommended</option>
          <option value="rating" {% if selected_sort == 'rating' %}selected{% endif %}>Highest rated</option>
          <option value="name" {% if selected_sort == 'name' %}selected{% endif %}>Name A–Z</option>
        </select>
      </div>
      <div class="ea-tools-actions">
        <button type="submit">Show destinations &#8594;</button>
        <a href="{% url 'places:attraction_carousel' %}?browse=all">Clear filters / Browse all</a>
      </div>
    </form>
  </section>
'''


def build_template(original: str) -> str:
    updated = exactly_once(original, '\n</style>\n{% endblock %}', FILTER_STYLE + '\n</style>\n{% endblock %}', 'Filter styles')
    updated = exactly_once(
        updated,
        '''  </section>

  {% if attractions %}
''',
        '  </section>\n' + FILTER_HTML + '\n  {% if attractions %}\n',
        'Filter toolbar placement',
    )
    updated = exactly_once(
        updated,
        '''            href="?page={{ page_obj.previous_page_number }}"
''',
        '''            href="?page={{ page_obj.previous_page_number }}&amp;q={{ search_query|urlencode }}&amp;category={{ selected_category|urlencode }}&amp;hobby={{ selected_hobby|urlencode }}&amp;sort={{ selected_sort|urlencode }}"
''',
        'Previous-page query preservation',
    )
    updated = exactly_once(
        updated,
        '''            href="?page={{ page_obj.next_page_number }}"
''',
        '''            href="?page={{ page_obj.next_page_number }}&amp;q={{ search_query|urlencode }}&amp;category={{ selected_category|urlencode }}&amp;hobby={{ selected_hobby|urlencode }}&amp;sort={{ selected_sort|urlencode }}"
''',
        'Next-page query preservation',
    )
    updated = exactly_once(
        updated,
        '''    Try another search or adjust your selected hobbies.
''',
        '''    Try another search term, change the category or hobby filter, or browse all destinations.
''',
        'Empty results guidance',
    )
    # Ensure clear search is reachable even when the filters return no results.
    updated = exactly_once(
        updated,
        '''      <a
        href="{% url 'hobbies:select' %}"
        class="ea-change-city"
      >
        Change Hobbies
      </a>
''',
        '''      <a
        href="{% url 'places:attraction_carousel' %}?browse=all"
        class="ea-change-city"
      >
        Browse All Destinations
      </a>
''',
        'Empty state browse-all link',
    )
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Check compatibility without modifying files')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    view = root / 'apps' / 'places' / 'views.py'
    template = root / 'templates' / 'places' / 'attraction_carousel.html'
    if not (root / 'manage.py').is_file() or not view.is_file() or not template.is_file():
        print('ERROR: Run this script inside the ExploreAnywhere project directory (where manage.py exists).')
        return 2

    old_view_bytes = view.read_bytes()
    old_template_bytes = template.read_bytes()
    old_view = old_view_bytes.decode('utf-8-sig').replace('\r\n', '\n')
    old_template = old_template_bytes.decode('utf-8-sig').replace('\r\n', '\n')
    if MARKER in old_view or MARKER in old_template:
        if MARKER in old_view and MARKER in old_template:
            print('ALREADY INSTALLED: Both Phase 5A files have the upgrade marker. No files changed.')
            return 0
        print('ERROR: Partial Phase 5A installation detected. No changes made. Please request assistance.')
        return 2

    try:
        new_view = build_view(old_view)
        new_template = build_template(old_template)
    except (ValueError, SyntaxError) as error:
        print(f'NOT SAFE TO PATCH: {error}')
        print('No files were changed. Please upload your latest views.py and template.')
        return 2

    print(('DRY RUN OK' if args.dry_run else 'READY') + ': Phase 5A direct search, verified filters, sorting and pagination are compatible.')
    print('  Target files: apps/places/views.py; templates/places/attraction_carousel.html')
    print('  Kept intact: recommendation weights, approved Kabankalan scope, MapTiler key, Leaflet script, database')
    if args.dry_run:
        print('  No files changed. Run without --dry-run to apply.')
        return 0

    backup = root / 'phase5_backups' / ('discovery-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    try:
        backup.mkdir(parents=True, exist_ok=False)
        (backup / 'views.py').write_bytes(old_view_bytes)
        (backup / 'attraction_carousel.html').write_bytes(old_template_bytes)
        # Preserve Windows line endings and any existing UTF-8 BOM.
        def matching_encoding(text, original_bytes):
            linebreak = '\r\n' if b'\r\n' in original_bytes else '\n'
            bom = b'\xef\xbb\xbf' if original_bytes.startswith(b'\xef\xbb\xbf') else b''
            return bom + text.replace('\n', linebreak).encode('utf-8')

        # Write only after both patches are fully validated and backed up.
        view.write_bytes(matching_encoding(new_view, old_view_bytes))
        template.write_bytes(matching_encoding(new_template, old_template_bytes))
    except OSError as error:
        # Avoid claiming a successful installation if one write failed.
        if backup.exists() and (backup / 'views.py').exists() and (backup / 'attraction_carousel.html').exists():
            try:
                view.write_bytes(old_view_bytes)
                template.write_bytes(old_template_bytes)
            except OSError:
                print(f'ERROR: Could not fully restore files. Use backups inside: {backup}')
                return 3
        print(f'ERROR: Patch was not installed: {error}')
        return 3

    print('SUCCESS: Explore Places Phase 5A discovery upgrade installed.')
    print('Backup:', backup.relative_to(root))
    print('No migrations, database, map settings, or other project files modified.')
    print('NEXT: python manage.py check')
    print('NEXT: Test /places/?browse=all, search, category, hobby, sorting, pagination, map on desktop and Android.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
