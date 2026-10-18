
from pathlib import Path
from datetime import datetime
import re
import shutil

# Files in your existing ExploreAnywhere project
views_path = Path("apps/cities/views.py")
js_path = Path("static/js/city_select.js")
css_path = Path("static/css/explore.css")
template_path = Path("templates/cities/city_selection.html")

paths = [views_path, js_path, css_path, template_path]

for path in paths:
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")

def read(path):
    return path.read_text(encoding="utf-8-sig")

views = read(views_path)
js = read(js_path)
css = read(css_path)
template = read(template_path)

# =============================================
# 1. DJANGO: ALLOW PENDING CITY SUBMISSIONS
# =============================================

start_match = re.search(
    r"(?m)^def choose_city\(request\):",
    views
)

if not start_match:
    raise SystemExit(
        "choose_city() not found. No changes made."
    )

start = start_match.start()

next_view = re.search(
    r"(?m)^(?:def |@)",
    views[start_match.end():]
)

end = (
    start_match.end() + next_view.start()
    if next_view else len(views)
)

choose_view = views[start:end]

# Remove the active-only filter in the POST view.
choose_view = re.sub(
    r'(?m)^[ \t]*status\s*=\s*["\']active["\'],?\s*\n',
    "",
    choose_view,
)

views = views[:start] + choose_view + views[end:]

# Allow a previously chosen Pending city to be
# restored when the user refreshes the page.
views = re.sub(
    r'filter\(\s*pk=selected_id,\s*status=["\']active["\']\s*\)',
    "filter(pk=selected_id)",
    views,
)

# =============================================
# 2. JAVASCRIPT: REBUILD CLICKABLE CITY CARDS
# =============================================

start_token = "function createCard(city) {"
end_token = "async function loadProvinces() {"

if start_token not in js or end_token not in js:
    raise SystemExit(
        "Expected city card functions not found. "
        "No changes made."
    )

start = js.index(start_token)
end = js.index(end_token, start)

new_create_card = r'''
function createCard(city) {
    const button = document.createElement("button");

    button.type = "button";
    button.className = "select-city-card";
    button.dataset.id = String(city.id);

    // Pending means attractions have not been
    // added yet. It does NOT disable city selection.
    const hasPlaces = city.active === true;

    if (!hasPlaces) {
        button.classList.add("pending");
    }

    const top = document.createElement("div");
    top.className = "select-card-top";

    const icon = document.createElement("span");
    icon.className = "select-card-icon";
    icon.innerHTML = svgIcon("pin");

    const check = document.createElement("span");
    check.className = "select-check";
    check.innerHTML = svgIcon("check");

    top.append(icon, check);

    const name = document.createElement("h3");
    name.textContent = city.name;

    const location = document.createElement("p");
    location.className = "select-card-location";
    location.textContent =
        `${city.province}, ${city.region}`;

    const bottom = document.createElement("div");
    bottom.className = "select-card-bottom";

    const badge = document.createElement("span");
    badge.className = hasPlaces
        ? "status-badge active"
        : "status-badge pending";

    badge.textContent = hasPlaces
        ? "Active"
        : "No places yet";

    const places = document.createElement("span");
    places.className = "place-number";

    places.textContent =
        `${city.places_count} places available`;

    bottom.append(badge, places);
    button.append(top, name, location, bottom);

    // Every city or municipality is selectable.
    button.addEventListener("click", () => {
        setSelected(city);
    });

    return button;
}

'''

js = js[:start] + new_create_card + js[end:]

# =============================================
# 3. CSS: REMOVE DISABLED PENDING APPEARANCE
# =============================================

css += """

/* All PSGC cities can be selected */
.explore-city-page .select-city-card.pending {
    opacity: 1 !important;
    cursor: pointer !important;
    pointer-events: auto !important;
}

.explore-city-page .select-city-card.pending:hover {
    border-color: #93b4ff;
}

.explore-city-page .select-city-card.selected {
    border: 2px solid #2563eb !important;
    background: #eff5ff !important;
    opacity: 1 !important;
}

.explore-city-page .select-city-card.selected .select-check {
    display: grid !important;
}
"""

# =============================================
# 4. FORCE THE BROWSER TO LOAD NEW JAVASCRIPT
# =============================================

template = re.sub(
    r"(\{%\s*static\s+['\"]js/city_select\.js['\"]\s*%\})"
    r"(?:\?v=[A-Za-z0-9_-]+)?",
    r"\1?v=selectable-v3",
    template,
)

# =============================================
# 5. BACK UP AND WRITE ALL CHANGES
# =============================================

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

updates = [
    (views_path, views),
    (js_path, js),
    (css_path, css),
    (template_path, template),
]

for path, contents in updates:
    backup = path.with_name(
        path.name + ".bak_" + stamp
    )
    shutil.copy2(path, backup)

    path.write_text(
        contents,
        encoding="utf-8",
    )

    print(f"UPDATED: {path}")
    print(f"BACKUP:  {backup}")

print()
print("Pending cities are now selectable.")
print("Database records and statuses were not changed.")
