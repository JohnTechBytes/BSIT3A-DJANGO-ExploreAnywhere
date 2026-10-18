
from pathlib import Path
import shutil

path = Path("templates/places/attraction_carousel.html")

if not path.exists():
    raise SystemExit("ERROR: Attraction template not found.")

html = path.read_text(encoding="utf-8-sig")

if 'id="ea-map-panel"' in html:
    raise SystemExit("Map integration is already installed.")

anchors = [
    "{% block extra_css %}",
    "</style>",
    '<section aria-label="City tourist attractions">',
    '<article class="ea-card">',
    'class="ea-carousel"',
    "{% block extra_js %}",
]

for anchor in anchors:
    if anchor not in html:
        raise SystemExit(
            f"ERROR: Missing template section: {anchor}"
        )

# Add Leaflet and new component styles.
css = """
<link rel="stylesheet"
 href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
"""

styles = """
.ea-view-switch {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
    margin-bottom: 20px;
}

.ea-view-button {
    border: 1px solid #d4dfed;
    border-radius: 11px;
    background: white;
    color: #183c6b;
    padding: 12px 18px;
    font-weight: 700;
    cursor: pointer;
}

.ea-view-button[aria-pressed="true"] {
    background: #0757d8;
    border-color: #0757d8;
    color: white;
}

#ea-attraction-map {
    height: 460px;
    width: 100%;
    border-radius: 18px;
    border: 1px solid #d4dfed;
    background: #e8f0fa;
    z-index: 0;
}

.ea-map-note {
    color: #60718d;
    font-size: 13px;
}

#ea-list-panel[hidden],
#ea-map-panel[hidden] {
    display: none !important;
}

@media (max-width: 700px) {
    #ea-attraction-map { height: 350px; }
}
"""

html = html.replace(
    "{% block extra_css %}",
    "{% block extra_css %}\n" + css,
    1,
)

html = html.replace(
    "</style>",
    styles + "\n</style>",
    1,
)

# Insert the display-mode buttons before the carousel.
buttons = """
<div class="ea-view-switch" role="group"
     aria-label="Results display mode">

    <button type="button" id="ea-list-button"
            class="ea-view-button"
            aria-pressed="true">
        List / Carousel
    </button>

    <button type="button" id="ea-map-button"
            class="ea-view-button"
            aria-pressed="false">
        Map View
    </button>

    <a class="ea-change-city"
       href="{% url 'hobbies:search' %}">
        Change Search
    </a>
</div>

<div id="ea-list-panel">
"""

import re

pattern = r'<div\s+class="ea-carousel"'

html, count = re.subn(
    pattern,
    lambda match: buttons + "\n" + match.group(0),
    html,
    count=1,
)

if count != 1:
    raise SystemExit(
        "ERROR: Carousel opening tag not found. No changes saved."
    )

# Store each card's coordinates for the map.
html = html.replace(
    '<article class="ea-card">',
    '''<article class="ea-card"
        {% if place.latitude != None and place.longitude != None %}
        data-lat="{{ place.latitude }}"
        data-lng="{{ place.longitude }}"
        {% endif %}>''',
    1,
)

# Insert map after the carousel, before pagination.
pagination_anchor = "{% if page_obj.has_other_pages %}"

map_section = """
</div>

<section id="ea-map-panel" hidden
         aria-label="Attractions map">

    <div id="ea-attraction-map"></div>

    <p id="ea-map-note" class="ea-map-note">
        Map shows attractions on this results page.
    </p>
</section>
"""

# Use the final carousel closing region as the insertion point.
closing = """
      </div>

    </section>
"""

if closing not in html:
    raise SystemExit(
        "ERROR: Carousel closing section not found. "
        "No changes saved."
    )

html = html.replace(
    closing,
    """
      </div>
""" + map_section + """
    </section>
""",
    1,
)

javascript = """
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js">
</script>

<script>
(function () {
    "use strict";

    const listButton =
        document.getElementById("ea-list-button");

    const mapButton =
        document.getElementById("ea-map-button");

    const listPanel =
        document.getElementById("ea-list-panel");

    const mapPanel =
        document.getElementById("ea-map-panel");

    const mapNote =
        document.getElementById("ea-map-note");

    if (!listButton || !mapButton ||
        !listPanel || !mapPanel) return;

    let map = null;

    function showView(view) {
        const showingMap = view === "map";

        listPanel.hidden = showingMap;
        mapPanel.hidden = !showingMap;

        listButton.setAttribute(
            "aria-pressed", String(!showingMap)
        );

        mapButton.setAttribute(
            "aria-pressed", String(showingMap)
        );

        if (!showingMap) return;

        if (!window.L) {
            mapNote.textContent =
                "Unable to load the map. Check your internet connection.";
            return;
        }

        if (!map) {
            map = L.map("ea-attraction-map", {
                scrollWheelZoom: false
            });

            L.tileLayer(
                "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
                {
                    attribution: "&copy; OpenStreetMap contributors",
                    maxZoom: 19
                }
            ).addTo(map);

            const coordinates = [];

            document.querySelectorAll(
                ".ea-card[data-lat][data-lng]"
            ).forEach(card => {
                const lat = Number(card.dataset.lat);
                const lng = Number(card.dataset.lng);

                if (!Number.isFinite(lat) ||
                    !Number.isFinite(lng) ||
                    Math.abs(lat) > 90 ||
                    Math.abs(lng) > 180) return;

                const name =
                    card.querySelector("h3")
                    ?.textContent.trim() || "Attraction";

                const category =
                    card.querySelector(".ea-category")
                    ?.textContent.trim() || "";

                const popup = document.createElement("div");
                const heading = document.createElement("strong");
                const description = document.createElement("p");

                heading.textContent = name;
                description.textContent = category;

                popup.append(heading, description);

                L.marker([lat, lng])
                    .bindPopup(popup)
                    .addTo(map);

                coordinates.push([lat, lng]);
            });

            if (coordinates.length) {
                map.fitBounds(
                    L.latLngBounds(coordinates).pad(0.15),
                    {maxZoom: 14}
                );

                mapNote.textContent =
                    coordinates.length +
                    " attractions mapped on this results page.";
            } else {
                map.setView([12.8797, 121.7740], 5);

                mapNote.textContent =
                    "No results on this page have valid coordinates.";
            }
        }

        requestAnimationFrame(() => map.invalidateSize());
    }

    listButton.addEventListener(
        "click", () => showView("list")
    );

    mapButton.addEventListener(
        "click", () => showView("map")
    );
})();
</script>
"""

html = html.replace(
    "{% block extra_js %}",
    "{% block extra_js %}\n" + javascript,
    1,
)

# Save only after all expected sections were found.
backup = path.with_suffix(".html.before-map.bak")
shutil.copy2(path, backup)

path.write_text(html, encoding="utf-8")

print("SUCCESS: ExploreAnywhere map integrated.")
print("Backup:", backup)
print("Next: python manage.py check")
