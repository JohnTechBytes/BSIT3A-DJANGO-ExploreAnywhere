#!/usr/bin/env python3
"""ExploreAnywhere Phase 5A.2: clearer search/recommendation UI.

From the ExploreAnywhere project root:
    python phase5a2_upgrade/exploreanywhere_phase5a2_clarity_upgrade.py --dry-run
    python phase5a2_upgrade/exploreanywhere_phase5a2_clarity_upgrade.py

Edits only apps/places/views.py and templates/places/attraction_carousel.html.
Creates byte-for-byte timestamped backups, includes a safe --restore mode.
Does not touch recommendation weights, DB, MapTiler key, map tile layers, or records.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import re
from datetime import datetime
from pathlib import Path
import sys

MARKER = 'exploreanywhere-phase5a2-discovery-clarity-v1'
PRIOR_MARKER = 'exploreanywhere-phase5a-discovery-controls-v1'


def replace_once(source: str, old: str, new: str, title: str) -> str:
    occurrences = source.count(old)
    if occurrences != 1:
        raise ValueError(f'{title}: expected one exact anchor, found {occurrences}.')
    return source.replace(old, new, 1)


def new_view(source: str) -> str:
    # Use the already-validated query/category/hobby/sort state. No scoring changes.
    old = '''    paginator = Paginator(attractions, 12)
    page = paginator.get_page(request.GET.get("page"))

    return render(
'''
    new = '''    paginator = Paginator(attractions, 12)
    page = paginator.get_page(request.GET.get("page"))

    # exploreanywhere-phase5a2-discovery-clarity-v1
    # Remove-one controls retain the other active filters and clear q from the
    # existing search session when the Search chip is removed.
    from urllib.parse import urlencode

    active_state = {
        "q": search_query,
        "category": selected_category,
        "hobby": selected_hobby,
        "sort": selected_sort,
    }
    active_filter_chips = []
    labels = (
        ("q", "Search", search_query),
        ("category", "Category", available_categories.get(selected_category, "")),
        ("hobby", "Hobby", available_hobbies.get(selected_hobby, "")),
        (
            "sort", "Sort",
            {"name": "Name A–Z", "rating": "Highest rated"}.get(selected_sort, ""),
        ),
    )
    for field, label, value in labels:
        if not value:
            continue
        remaining_state = dict(active_state)
        remaining_state[field] = "recommended" if field == "sort" else ""
        active_filter_chips.append({
            "label": f"{label}: {value}",
            "remove_url": "?" + urlencode(remaining_state),
        })

    return render(
'''
    updated = replace_once(source, old, new, 'Add removable filter chips to view context')
    updated = replace_once(updated,
        '            "selected_sort": selected_sort,\n',
        '            "selected_sort": selected_sort,\n            "active_filter_chips": active_filter_chips,\n',
        'Pass active filter chips to template',
    )
    ast.parse(updated)
    return updated


STYLES = '''
/* exploreanywhere-phase5a2-discovery-clarity-v1: scores, filters, compact results */
.ea-summary-summary {display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;}
.ea-summary-note {color:#dce9ff;font-size:12px;margin-top:6px;}
.ea-current-filters {margin-top:16px;padding-top:13px;border-top:1px solid #edf2f9;}
.ea-current-filters-title {display:block;font-size:12px;font-weight:800;color:#365373;margin:0 0 10px;}
.ea-filter-chips {display:flex;flex-wrap:wrap;gap:8px;align-items:center;}
.ea-filter-chip {display:inline-flex;align-items:center;gap:9px;border:1px solid #bcd7ff;
  border-radius:100px;padding:7px 12px;max-width:100%;background:#eff6ff;color:#0c4b9d;
  text-decoration:none;font-size:12px;font-weight:700;line-height:1.35;overflow-wrap:anywhere;}
.ea-filter-chip:hover {background:#dceeff;border-color:#8dbbff;}
.ea-filter-chip:focus-visible {outline:3px solid #82b5ff;outline-offset:2px;}
.ea-filter-chip-remove {font-size:15px;line-height:1;}
.ea-filter-reset {font-size:12px;color:#0757d8;font-weight:800;padding:8px;text-decoration:underline;}
.ea-filter-reset:focus-visible {outline:3px solid #82b5ff;outline-offset:2px;}
.ea-search-relevance {font-size:12px;font-weight:750;line-height:1.4;
  margin:0 0 10px;color:#0c704d;}
.ea-match-badge--unscored {background:#f1f5f9;color:#334155;white-space:normal;}
.ea-score-guidance {margin:0 0 14px;color:#546882;font-size:13px;line-height:1.6;}
.ea-carousel--compact {display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,280px),1fr));
  align-items:stretch;overflow:visible;scroll-snap-type:none;scroll-behavior:auto;gap:18px;}
.ea-carousel--compact .ea-card {flex:none;width:100%;max-width:none;min-width:0;scroll-snap-align:unset;}
.ea-carousel--single {display:block;max-width:890px;}
.ea-carousel--single .ea-card {display:grid;grid-template-columns:minmax(240px,41%) minmax(0,1fr);width:100%;}
.ea-carousel--single .ea-card-image {height:auto;min-height:275px;}
.ea-carousel--single .ea-card-body {padding:24px;}
.ea-carousel--single .ea-card h3 {font-size:22px;}
@media(max-width:640px) {
  .ea-carousel--single .ea-card {display:flex;flex-direction:column;}
  .ea-carousel--single .ea-card-image {min-height:190px;height:190px;}
  .ea-carousel--single .ea-card-body {padding:19px;}
  .ea-carousel--single .ea-card h3 {font-size:18px;}
  .ea-carousel--compact {grid-template-columns:minmax(0,1fr);}
  .ea-carousel--compact .ea-card {width:100%;max-width:none;}
}
'''


def new_template(source: str) -> str:
    updated = replace_once(source,
        '\n</style>\n{% endblock %}',
        STYLES + '\n</style>\n{% endblock %}',
        'Additional mobile-first styles',
    )

    updated = replace_once(updated, '''  <section class="ea-summary">
    <strong>
      {{ total_attractions }}
      Approved Attraction{{ total_attractions|pluralize }}
    </strong>

    <p>
''', '''  <section class="ea-summary" aria-live="polite">
    <strong>
      {% if search_query or selected_category or selected_hobby %}
        {{ total_attractions }} Matching Destination{{ total_attractions|pluralize }}
      {% else %}
        {{ published_total }} Published Destination{{ published_total|pluralize }}
      {% endif %}
    </strong>
    {% if search_query or selected_category or selected_hobby %}
      <p class="ea-summary-note">Filtered from {{ published_total }} verified, published Kabankalan destinations.</p>
    {% else %}
      <p class="ea-summary-note">All verified, published Kabankalan destinations.</p>
    {% endif %}

    <p>
''', 'Search-specific summary text')

    updated = replace_once(updated, '''    </form>
  </section>

  {% if attractions %}
''', '''    </form>
    {% if active_filter_chips %}
      <div class="ea-current-filters" aria-label="Active discovery settings">
        <span class="ea-current-filters-title">Active search and display settings</span>
        <div class="ea-filter-chips">
          {% for chip in active_filter_chips %}
            <a class="ea-filter-chip" href="{{ chip.remove_url }}" aria-label="Remove {{ chip.label }}">
              {{ chip.label }} <span class="ea-filter-chip-remove" aria-hidden="true">&times;</span>
            </a>
          {% endfor %}
          <a class="ea-filter-reset" href="{% url 'places:attraction_carousel' %}?browse=all">Clear all</a>
        </div>
      </div>
    {% endif %}
  </section>

  {% if attractions %}
''', 'Add server-generated filter chips')

    updated = replace_once(updated, '''  {% if search_query %}
    Results for "{{ search_query }}"
  {% else %}
    Places to Explore
  {% endif %}
''', '''  {% if search_query %}
    Results for "{{ search_query }}"
  {% elif selected_category or selected_hobby %}
    Filtered Kabankalan Destinations
  {% else %}
    Places to Explore
  {% endif %}
''', 'Results title when filters active')

    updated = replace_once(updated, '''        <div class="ea-carousel-controls">
          <button
''', '''        {% if total_attractions > 3 %}<div class="ea-carousel-controls">
          <button
''', 'Hide pointless arrows for compact results')
    updated = replace_once(updated, '''            &#8594;
          </button>
        </div>
      </div>
''', '''            &#8594;
          </button>
        </div>{% endif %}
      </div>
''', 'Close conditional carousel arrows')

    updated = replace_once(updated, '''<p class="ea-match-explainer">Scores combine selected-hobby overlap and available visitor ratings, then normalize the available signals. A nonzero score does not always mean a hobby match. GPS distance is not included.</p>
''', '''<p class="ea-score-guidance" id="ea-score-guidance">Finding a destination with search or filters does not mean it matches your personal hobbies. Personalized relevance is calculated using selected hobbies and available ratings, normalized over available signals. A lower percentage is not a destination-quality rating. No GPS distance is scored. Gray map markers mean there is not enough personalization information; colored map markers use the displayed score.</p>
''', 'Explain relevance versus search and map interpretation')

    updated = replace_once(updated, '''        class="ea-carousel"
        id="ea-carousel"
''', '''        class="ea-carousel{% if total_attractions <= 3 %} ea-carousel--compact{% endif %}{% if total_attractions == 1 %} ea-carousel--single{% endif %}"
        id="ea-carousel"
''', 'Apply compact result layouts')

    updated = replace_once(updated, '''          data-match="{{ place.match_percent|default_if_none:'0' }}"
          data-hobby-match="{{ place.has_hobby_match|yesno:'true,false' }}"
''', '''          data-match="{{ place.match_percent|default_if_none:'0' }}"
          data-score-available="{% if selected_hobbies or place.avg_rating %}true{% else %}false{% endif %}"
          data-rating-available="{% if place.avg_rating %}true{% else %}false{% endif %}"
          data-hobby-match="{{ place.has_hobby_match|yesno:'true,false' }}"
''', 'Add neutral-marker status without changing score')

    updated = replace_once(updated, '''              <h3>{{ place.title }}</h3>
              {% if place.match_percent is not None %}
              <span class="ea-match-badge" title="Uses available hobby and rating information; distance is not scored.">
                {{ place.match_percent }}% Recommendation Score
              </span>
              {% if place.has_hobby_match %}
                <p class="ea-match-reason">Matching hobbies: {{ place.matched_hobbies|join:", " }}</p>
              {% elif place.review_count %}
                <p class="ea-match-reason">No selected hobby matches. Existing ratings contribute to this score.</p>
              {% else %}
                <p class="ea-match-reason">No selected hobby match or usable rating data.</p>
              {% endif %}
              {% endif %}
''', '''              <h3>{{ place.title }}</h3>
              {% if search_query %}
                <p class="ea-search-relevance">Search result for "{{ search_query }}"</p>
              {% endif %}
              {% if selected_hobbies or place.avg_rating %}
                <span class="ea-match-badge" title="Personalized relevance is based on selected hobbies and/or available ratings; not on search relevance or destination quality.">
                  {{ place.match_percent }}% Personalized Relevance
                </span>
                {% if place.has_hobby_match %}
                  <p class="ea-match-reason">Matching selected hobbies: {{ place.matched_hobbies|join:", " }}.</p>
                {% elif place.avg_rating %}
                  <p class="ea-match-reason">No selected hobby match. Available visitor ratings contribute to this score.</p>
                {% else %}
                  <p class="ea-match-reason">No selected hobby match or rating signal. This is not a quality rating.</p>
                {% endif %}
              {% else %}
                <span class="ea-match-badge ea-match-badge--unscored">Not scored yet</span>
                <p class="ea-match-reason">No selected hobbies or visitor ratings are available. Choose hobbies to personalize results.</p>
              {% endif %}
''', 'Make score badge separate from search relevance')

    updated = replace_once(updated, '''      <h2>{% if search_query %}No matching destinations found{% else %}No approved attractions yet{% endif %}</h2>
''', '''      <h2>{% if search_query or selected_category or selected_hobby %}No matching destinations found{% else %}No published destinations yet{% endif %}</h2>
''', 'Clarify empty results')

    updated = replace_once(updated, '''  {% if search_query %}
    No approved attractions matching
    "{{ search_query }}" were found in
    {{ selected_city.name }}.
    Try another search term, change the category or hobby filter, or browse all destinations.
  {% else %}
    Destinations for {{ selected_city.name }}
    are still being reviewed.
  {% endif %}
''', '''  {% if search_query or selected_category or selected_hobby %}
    No published Kabankalan destinations matched the current search and filters.
    Try a different term or remove a filter, or browse all destinations.
  {% else %}
    Destinations for {{ selected_city.name }} are still being reviewed.
  {% endif %}
''', 'More helpful filter-aware empty-state text')

    updated = replace_once(updated, '''            matchPercent: Number(card.dataset.match || 0),
            hobbyMatch: card.dataset.hobbyMatch === "true",
''', '''            matchPercent: Number(card.dataset.match || 0),
            scoreAvailable: card.dataset.scoreAvailable === "true",
            ratingAvailable: card.dataset.ratingAvailable === "true",
            hobbyMatch: card.dataset.hobbyMatch === "true",
''', 'Read availability of personalized score in map cards')

    updated = replace_once(updated, '''        const coordinates = document.createElement("p");
        coordinates.textContent =
''', '''        const relevance = document.createElement("p");
        relevance.textContent = attraction.scoreAvailable
            ? attraction.matchPercent + "% personalized relevance (not a quality rating)"
            : "Personalized relevance not scored yet";

        const coordinates = document.createElement("p");
        coordinates.textContent =
''', 'Add score clarity in map details')
    updated = replace_once(updated, '''            category,
            title,
            description,
            coordinates,
''', '''            category,
            title,
            description,
            relevance,
            coordinates,
''', 'Append map relevance text')

    updated = replace_once(updated, '''          el.innerHTML = '<strong>Recommendation match</strong><div><span style="color:#16a34a">●</span> 80–100% High</div><div><span style="color:#f59e0b">●</span> 50–79% Medium</div><div><span style="color:#dc2626">●</span> 0–49% Low</div>';
''', '''          el.innerHTML = '<strong>Personalized relevance</strong><div><span style="color:#16a34a">●</span> 80–100% Strong</div><div><span style="color:#f59e0b">●</span> 50–79% Moderate</div><div><span style="color:#dc2626">●</span> 0–49% Limited</div><div><span style="color:#64748b">●</span> Not scored</div><small>Scores are not quality ratings</small>';
''', 'Legend matches scores and neutral color')

    updated = replace_once(updated, '''const markerColor =
    score >= 80 ? "#16a34a" :
    score >= 50 ? "#f59e0b" :
                  "#dc2626";
''', '''const markerColor = !attraction.scoreAvailable ? "#64748b" :
    score >= 80 ? "#16a34a" :
    score >= 50 ? "#f59e0b" :
                  "#dc2626";
''', 'Neutral marker when no scoring signals')

    updated = replace_once(updated, '''popupMatch.textContent =
    attraction.matchPercent + "% Recommendation Match";

const popupReason = document.createElement("p");
                popupReason.textContent = attraction.hobbyMatch
                    ? "Matching hobbies: " + attraction.matchedHobbies
                    : "No selected hobby match; score may reflect ratings.";
''', '''popupMatch.textContent = attraction.scoreAvailable
    ? attraction.matchPercent + "% Personalized Relevance"
    : "Not scored yet";

const popupReason = document.createElement("p");
                popupReason.textContent = !attraction.scoreAvailable
                    ? "Choose hobbies to personalize results; there are no visitor rating signals yet."
                    : attraction.hobbyMatch
                        ? "Matching hobbies: " + attraction.matchedHobbies
                        : attraction.ratingAvailable
                            ? "No selected hobby match; available visitor ratings contribute. Not a quality rating."
                            : "No selected hobby match or visitor ratings. Not a quality rating.";
''', 'Popup explanations match score status')
    return updated


def same_newlines(text: str, source_bytes: bytes) -> bytes:
    ending = '\r\n' if b'\r\n' in source_bytes else '\n'
    bom = b'\xef\xbb\xbf' if source_bytes.startswith(b'\xef\xbb\xbf') else b''
    return bom + text.replace('\n', ending).encode('utf-8')


def read_normalized(path: Path) -> tuple[bytes, str]:
    data = path.read_bytes()
    return data, data.decode('utf-8-sig').replace('\r\n', '\n')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Validate exact patch anchors; write nothing')
    parser.add_argument('--restore', metavar='BACKUP_DIR', help='Restore only two files from this installer backup')
    args = parser.parse_args()

    root = Path.cwd().resolve()
    view = root / 'apps' / 'places' / 'views.py'
    template = root / 'templates' / 'places' / 'attraction_carousel.html'
    if not (root / 'manage.py').is_file() or not view.is_file() or not template.is_file():
        print('ERROR: Run inside ExploreAnywhere project directory containing manage.py.')
        return 2
    if args.restore:
        backup = Path(args.restore).resolve()
        try:
            # Avoid overwriting pre-existing changed files or arbitrary backup directories.
            if not backup.is_dir() or not backup.name.startswith('clarity-') or backup.parent != root / 'phase5_backups':
                raise ValueError('Expected a phase5_backups/clarity-* directory from this installer.')
            old_view = (backup / 'views.py').read_bytes()
            old_template = (backup / 'attraction_carousel.html').read_bytes()
            present_view, normalized_view = read_normalized(view)
            present_template, normalized_template = read_normalized(template)
            if MARKER not in normalized_view or MARKER not in normalized_template:
                raise ValueError('Not a complete Phase 5A.2 installation; refusing to overwrite.')
            view.write_bytes(old_view)
            template.write_bytes(old_template)
            print('RESTORED: Phase 5A.2 files restored from', backup.relative_to(root))
            return 0
        except (ValueError, OSError) as exc:
            print('RESTORE FAILED:', exc)
            return 2

    vdata, vtext = read_normalized(view)
    tdata, ttext = read_normalized(template)
    if MARKER in vtext or MARKER in ttext:
        if MARKER in vtext and MARKER in ttext:
            print('ALREADY INSTALLED: Phase 5A.2 changes are present in both files.')
            return 0
        print('ERROR: Partial installation marker detected; no changes made.')
        return 2
    if PRIOR_MARKER not in vtext or PRIOR_MARKER not in ttext:
        print('NOT SAFE TO PATCH: Install Phase 5A first. No files changed.')
        return 2

    try:
        revised_view = new_view(vtext)
        revised_template = new_template(ttext)
    except (SyntaxError, ValueError) as exc:
        print('NOT SAFE TO PATCH:', exc)
        print('No files changed. Upload your latest views.py and attraction_carousel.html.')
        return 2

    # Explicitly preserve the existing map provider key/tiles and core scoring invocation.
    provider_pattern = r'const mapTilerKey = [^;]*;'
    if re.findall(provider_pattern, ttext) != re.findall(provider_pattern, revised_template):
        print('ERROR: Map provider configuration mismatch; patch refused.')
        return 2
    required_view = (
        'attractions = rank_kabankalan_places(',
        'city=city, is_active=True, is_verified=True',
        'attractions = attractions.filter(search_filter)',
    )
    if any(vtext.count(anchor) != revised_view.count(anchor) for anchor in required_view):
        print('ERROR: An existing recommendation or search anchor changed; patch refused.')
        return 2
    print('DRY RUN OK:' if args.dry_run else 'PATCH READY:', 'Phase 5A.2 score, results, filters and layout patch is compatible.')
    print('Files: apps/places/views.py, templates/places/attraction_carousel.html')
    print('Preserved: ranking formula, Kabankalan filtering, NLP search, MapTiler/Leaflet layers, DB.')
    if args.dry_run:
        return 0

    backup = root / 'phase5_backups' / ('clarity-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    try:
        backup.mkdir(parents=True, exist_ok=False)
        (backup / 'views.py').write_bytes(vdata)
        (backup / 'attraction_carousel.html').write_bytes(tdata)
        try:
            view.write_bytes(same_newlines(revised_view, vdata))
            template.write_bytes(same_newlines(revised_template, tdata))
        except OSError:
            view.write_bytes(vdata)
            template.write_bytes(tdata)
            raise
    except OSError as exc:
        print('ERROR: Installer could not complete:', exc)
        print('Check original files and backup:', backup)
        return 3

    print('SUCCESS: Phase 5A.2 discovery clarity installed.')
    print('Updated only the two Places files. Backup:', backup.relative_to(root))
    print('No database modifications, migrations, or provider key changes.')
    print('To restore, run: python <installer-script> --restore "' + str(backup.relative_to(root)) + '"')
    print('Next: python manage.py check; verify single-result search + Map View, filters and Android.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
