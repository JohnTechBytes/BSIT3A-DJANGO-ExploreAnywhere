
# EXPLOREANYWHERE - PROVINCE AND CITY SELECTION
$ErrorActionPreference = "Stop"

if (!(Test-Path "manage.py")) {
    Write-Host "Open your Django project folder first!" -ForegroundColor Red
    return
}

function Save-File($path, $content) {
    $folder = Split-Path $path -Parent
    if ($folder) {
        New-Item -ItemType Directory -Force $folder | Out-Null
    }
    if (Test-Path $path) {
        Copy-Item $path "$path.bak_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
    }
    Set-Content $path $content -Encoding UTF8
    Write-Host "Created/updated: $path" -ForegroundColor Cyan
}

# 1. DJANGO VIEWS

$views = @'
from itertools import groupby

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, NoReverseMatch
from django.views.decorators.http import require_POST

from .models import City


@login_required
def select_city(request):
    cities = list(
        City.objects.filter(
            status=City.Status.ACTIVE
        ).order_by("province", "name")
    )

    province_groups = [
        {
            "province": province,
            "cities": list(group)
        }
        for province, group in groupby(
            cities,
            key=lambda city: city.province
        )
    ]

    return render(
        request,
        "cities/select_city.html",
        {
            "province_groups": province_groups,
            "province_total": len(province_groups),
            "city_total": len(cities),
            "selected_id": request.session.get(
                "selected_city_id"
            ),
        }
    )


@login_required
@require_POST
def choose_city(request):
    city_id = request.POST.get("city_id", "").strip()

    if not city_id.isdigit():
        messages.error(
            request,
            "Please select a city first."
        )
        return redirect("city_selection")

    city = get_object_or_404(
        City,
        pk=int(city_id),
        status=City.Status.ACTIVE
    )

    request.session["selected_city_id"] = city.pk
    request.session["selected_city_name"] = city.name
    request.session["selected_province"] = city.province

    for route in (
        "hobby_selection",
        "hobbies:select",
        "select_hobbies",
    ):
        try:
            return redirect(reverse(route))
        except NoReverseMatch:
            pass

    messages.success(
        request,
        f"{city.name}, {city.province} selected successfully."
    )

    return redirect("city_selection")
'@

Save-File "apps\cities\selection_views.py" $views


# 2. CITY URLS

$cityUrls = @'
from django.urls import path
from .selection_views import select_city, choose_city

urlpatterns = [
    path("", select_city, name="city_selection"),
    path("choose/", choose_city, name="city_choose"),
]
'@

Save-File "apps\cities\selection_urls.py" $cityUrls


# 3. REGISTER CITIES IN DJANGO ADMIN

$adminPath = "apps\cities\admin.py"

$adminText = if (Test-Path $adminPath) {
    Get-Content $adminPath -Raw -Encoding UTF8
} else {
    ""
}

if ($adminText -notmatch "EXPLOREANYWHERE_PROVINCE_ADMIN") {

$adminText += @'


# EXPLOREANYWHERE_PROVINCE_ADMIN
from django.contrib import admin as ea_admin
from .models import City as EA_City

class EACityAdmin(ea_admin.ModelAdmin):
    list_display = (
        "name", "province", "country", "status"
    )
    list_filter = (
        "province", "status", "country"
    )
    search_fields = (
        "name", "province"
    )
    prepopulated_fields = {
        "slug": ("name",)
    }

if not ea_admin.site.is_registered(EA_City):
    ea_admin.site.register(EA_City, EACityAdmin)
'@

Save-File $adminPath $adminText
}


# 4. DATABASE SEED COMMAND

$seed = @'
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from apps.cities.models import City


# Approximate city-center coordinates for development.
# Verify coordinates before using them for precise navigation.
CITIES = [
    ("Bacolod", "Negros Occidental", "10.6765", "122.9509"),
    ("Kabankalan", "Negros Occidental", "9.9889", "122.8142"),
    ("Silay", "Negros Occidental", "10.8000", "122.9770"),
    ("Bago", "Negros Occidental", "10.5333", "122.8333"),
    ("Sipalay", "Negros Occidental", "9.7540", "122.4030"),
    ("Iloilo City", "Iloilo", "10.7202", "122.5621"),
    ("Passi City", "Iloilo", "11.1075", "122.6414"),
    ("Cebu City", "Cebu", "10.3157", "123.8854"),
    ("Mandaue City", "Cebu", "10.3333", "123.9333"),
    ("Lapu-Lapu City", "Cebu", "10.3100", "123.9490"),
    ("Digos City", "Davao del Sur", "6.7490", "125.3570"),
]


class Command(BaseCommand):
    help = "Create starter cities grouped by province."

    def handle(self, *args, **kwargs):
        created = 0

        for name, province, lat, lng in CITIES:
            if City.objects.filter(
                name__iexact=name
            ).exists():
                continue

            slug = slugify(name)

            if City.objects.filter(slug=slug).exists():
                continue

            City.objects.create(
                name=name,
                slug=slug,
                province=province,
                country="Philippines",
                status=City.Status.ACTIVE,
                latitude=lat,
                longitude=lng,
            )

            created += 1

        total = City.objects.filter(
            status=City.Status.ACTIVE
        ).count()

        self.stdout.write(
            self.style.SUCCESS(
                f"Added {created} cities. Active cities: {total}"
            )
        )
'@

Save-File "apps\cities\management\commands\seed_cities.py" $seed


# 5. CITY SELECTION HTML

$template = @'
{% load static %}
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Select City | ExploreAnywhere</title>

<style>
:root {
    --navy: #101a2e;
    --blue: #1769ff;
    --muted: #64748b;
    --border: #e2e8f0;
}

* { box-sizing: border-box; }

body {
    margin: 0;
    background: #f4f7fd;
    color: var(--navy);
    font-family: Inter, "Segoe UI", Arial, sans-serif;
}

nav {
    min-height: 74px;
    background: var(--navy);
    padding: 15px 6%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
}

.brand {
    font-size: 22px;
    font-weight: 800;
    color: white;
    text-decoration: none;
}

.brand span { color: #60a5fa; }

.nav-actions {
    display: flex;
    gap: 20px;
    align-items: center;
}

.nav-actions a {
    color: #cbd5e1;
    text-decoration: none;
    font-size: 13px;
    font-weight: 700;
}

.logout {
    background: var(--blue);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 11px 18px;
    cursor: pointer;
    font-weight: 700;
}

.container {
    max-width: 1160px;
    margin: auto;
    padding: 65px 22px 90px;
}

.heading {
    text-align: center;
    margin-bottom: 38px;
}

.step {
    display: inline-block;
    background: #e8f0ff;
    color: var(--blue);
    padding: 8px 15px;
    border-radius: 30px;
    font-size: 12px;
    font-weight: 800;
}

.heading h1 {
    font-size: clamp(30px, 4vw, 44px);
    margin: 18px 0 12px;
    letter-spacing: -1px;
}

.heading p {
    color: var(--muted);
    font-size: 15px;
    line-height: 1.6;
}

.filters {
    display: grid;
    grid-template-columns: 270px 1fr;
    gap: 18px;
    margin-bottom: 25px;
}

.filter label {
    display: block;
    font-size: 13px;
    font-weight: 700;
    margin-bottom: 9px;
}

.filter select,
.filter input {
    width: 100%;
    padding: 15px 16px;
    border: 1px solid var(--border);
    background: white;
    border-radius: 11px;
    font-size: 14px;
    outline-color: var(--blue);
}

.summary {
    color: var(--muted);
    font-size: 13px;
    margin: 20px 0 30px;
    display: flex;
    justify-content: space-between;
}

.province-group {
    margin-bottom: 38px;
}

.province-header {
    display: flex;
    align-items: center;
    gap: 12px;
    padding-bottom: 15px;
    margin-bottom: 20px;
    border-bottom: 1px solid var(--border);
}

.province-header h2 {
    font-size: 20px;
    margin: 0;
}

.province-count {
    background: #e3efff;
    color: var(--blue);
    padding: 5px 12px;
    border-radius: 25px;
    font-size: 11px;
    font-weight: 700;
}

.city-grid {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
    gap: 20px;
}

.city-card {
    text-align: left;
    display: flex;
    flex-direction: column;
    width: 100%;
    min-width: 0;
    overflow: hidden;
    border: 2px solid var(--border);
    border-radius: 17px;
    background: white;
    color: var(--navy);
    font: inherit;
    cursor: pointer;
    transition: .2s;
    padding: 0;
}

.city-card:hover {
    transform: translateY(-3px);
    border-color: #93c5fd;
    box-shadow: 0 12px 25px rgba(23,105,255,.10);
}

.city-card.selected {
    border-color: var(--blue);
    box-shadow: 0 0 0 3px #dbeafe;
}

.city-visual {
    width: 100%;
    height: 105px;
    background: linear-gradient(125deg,#dbeafe,#93c5fd);
    display: grid;
    place-items: center;
    font-size: 35px;
    overflow: hidden;
}

.city-visual img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.city-info {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    padding: 18px;
}

.city-info h3 {
    margin: 0 0 7px;
    font-size: 17px;
}

.city-info p {
    margin: 0;
    color: var(--muted);
    font-size: 12px;
}

.checkmark {
    color: var(--blue);
    font-size: 24px;
    opacity: 0;
}

.city-card.selected .checkmark { opacity: 1; }

.actions {
    position: sticky;
    bottom: 12px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 20px;
    background: white;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 18px 22px;
    margin-top: 35px;
    box-shadow: 0 8px 30px rgba(16,26,46,.09);
}

.actions strong { font-size: 15px; }

.actions p {
    color: var(--muted);
    margin: 6px 0 0;
    font-size: 12px;
}

.continue {
    border: none;
    border-radius: 11px;
    background: var(--blue);
    color: white;
    padding: 15px 27px;
    font-weight: 800;
    cursor: pointer;
}

.continue:disabled {
    opacity: .45;
    cursor: not-allowed;
}

.notice {
    background: #dbeafe;
    color: #1d4ed8;
    padding: 14px;
    border-radius: 10px;
    margin-bottom: 20px;
}

.empty {
    padding: 25px;
    text-align: center;
    background: white;
    color: var(--muted);
    border: 1px dashed #bfdbfe;
    border-radius: 13px;
}

[hidden] { display: none !important; }

@media(max-width:900px) {
    .city-grid {
        grid-template-columns: repeat(2,minmax(0,1fr));
    }
}

@media(max-width:600px) {
    nav { padding: 15px; }
    .brand { font-size: 17px; }
    .nav-actions { gap: 9px; }
    .nav-actions a { font-size: 11px; }
    .logout { padding: 10px; }

    .container { padding: 40px 16px 65px; }

    .filters,
    .city-grid { grid-template-columns: 1fr; }

    .actions {
        flex-direction: column;
        align-items: stretch;
    }

    .continue { width: 100%; }
}
</style>
</head>

<body>

<nav>
    <a href="/" class="brand">
        ⌖ Explore<span>Anywhere</span>
    </a>

    <div class="nav-actions">
        <a href="/">← Back to Home</a>

        {% if user.is_authenticated %}
        <form method="post" action="{% url 'logout' %}" style="margin:0">
            {% csrf_token %}
            <button type="submit" class="logout">Logout</button>
        </form>
        {% else %}
        <a href="/accounts/login/">Login</a>
        {% endif %}
    </div>
</nav>

<main class="container">

    <div class="heading">
        <span class="step">STEP 1 OF 2 — DESTINATION</span>

        <h1>Where would you like to explore?</h1>

        <p>
            Select a province and city to discover places
            based on your interests.
        </p>
    </div>

    {% for message in messages %}
        <div class="notice">{{ message }}</div>
    {% endfor %}

    <div class="filters">
        <div class="filter">
            <label for="province-filter">Select Province</label>

            <select id="province-filter">
                <option value="">All Provinces</option>

                {% for group in province_groups %}
                <option value="{{ group.province }}">
                    {{ group.province }}
                </option>
                {% endfor %}
            </select>
        </div>

        <div class="filter">
            <label for="city-search">Search Cities</label>

            <input
                type="search"
                id="city-search"
                placeholder="Search Kabankalan, Bacolod, Cebu..."
                autocomplete="off"
            >
        </div>
    </div>

    <div class="summary">
        <span>
            {{ province_total }} provinces · {{ city_total }} cities
        </span>
        <span id="visible-count"></span>
    </div>

    <form method="post" action="{% url 'city_choose' %}">
        {% csrf_token %}

        <input
            type="hidden"
            name="city_id"
            id="selected-id"
            value="{{ selected_id|default:'' }}"
        >

        {% for group in province_groups %}

        <section
            class="province-group"
            data-province="{{ group.province }}"
        >

            <div class="province-header">
                <h2>📍 {{ group.province }}</h2>

                <span class="province-count">
                    {{ group.cities|length }} Cities
                </span>
            </div>

            <div class="city-grid">

                {% for city in group.cities %}

                <button
                    type="button"
                    class="city-card {% if selected_id == city.pk %}selected{% endif %}"
                    data-id="{{ city.pk }}"
                    data-name="{{ city.name }}"
                    data-province="{{ city.province }}"
                    aria-pressed="{% if selected_id == city.pk %}true{% else %}false{% endif %}"
                >

                    <div class="city-visual">
                        {% if city.banner_image %}
                        <img
                            src="{{ city.banner_image.url }}"
                            alt="{{ city.name }}"
                        >
                        {% else %}
                        🏙️
                        {% endif %}
                    </div>

                    <div class="city-info">
                        <div>
                            <h3>{{ city.name }}</h3>
                            <p>{{ city.province }}, Philippines</p>
                        </div>

                        <span class="checkmark">✓</span>
                    </div>

                </button>

                {% endfor %}

            </div>

        </section>

        {% empty %}
        <div class="empty">
            No cities available. Add cities through Django Admin.
        </div>
        {% endfor %}

        <div class="empty" id="no-results" hidden>
            No cities match your search.
        </div>

        <div class="actions">
            <div>
                <strong id="selection-label">
                    Choose a city to continue
                </strong>
                <p>
                    Your selected city will be saved for recommendations.
                </p>
            </div>

            <button
                type="submit"
                id="continue-btn"
                class="continue"
                disabled
            >
                Continue to Hobbies →
            </button>
        </div>
    </form>
</main>

<script>
document.addEventListener("DOMContentLoaded", function() {
    const cards = [...document.querySelectorAll(".city-card")];
    const sections = [...document.querySelectorAll(".province-group")];

    const province = document.getElementById("province-filter");
    const search = document.getElementById("city-search");
    const selected = document.getElementById("selected-id");
    const button = document.getElementById("continue-btn");
    const label = document.getElementById("selection-label");
    const count = document.getElementById("visible-count");

    function selectCity(id) {
        let chosen = null;

        cards.forEach(card => {
            const active = card.dataset.id === String(id);

            card.classList.toggle("selected", active);
            card.setAttribute("aria-pressed", String(active));

            if (active) chosen = card;
        });

        selected.value = chosen ? chosen.dataset.id : "";
        button.disabled = !chosen;

        label.textContent = chosen
            ? "Selected: " + chosen.dataset.name +
              ", " + chosen.dataset.province
            : "Choose a city to continue";
    }

    function filterCities() {
        const selectedProvince = province.value.toLowerCase();
        const query = search.value.trim().toLowerCase();

        let visible = 0;

        sections.forEach(section => {
            let matches = 0;

            section.querySelectorAll(".city-card").forEach(card => {
                const cityName = card.dataset.name.toLowerCase();
                const cityProvince = card.dataset.province.toLowerCase();

                const provinceMatch =
                    !selectedProvince ||
                    selectedProvince === cityProvince;

                const searchMatch =
                    !query ||
                    cityName.includes(query) ||
                    cityProvince.includes(query);

                const show = provinceMatch && searchMatch;

                card.hidden = !show;

                if (show) {
                    matches++;
                    visible++;
                }
            });

            section.hidden = matches === 0;
        });

        count.textContent = visible + " shown";

        document.getElementById("no-results").hidden =
            visible !== 0 || cards.length === 0;
    }

    cards.forEach(card => {
        card.addEventListener("click", function() {
            selectCity(card.dataset.id);
        });
    });

    province.addEventListener("change", filterCities);
    search.addEventListener("input", filterCities);

    selectCity(selected.value);
    filterCities();
});
</script>

</body>
</html>
'@

Save-File "templates\cities\select_city.html" $template


# 6. REGISTER CITY URL IN PROJECT

$urlPath = "mysite\urls.py"
$urls = Get-Content $urlPath -Raw -Encoding UTF8

if ($urls -notmatch "apps\.cities\.selection_urls") {

    if ($urls -notmatch "(?m)^from django\.urls import .*\binclude\b") {
        $urls = "from django.urls import include`r`n" + $urls
    }

    if ($urls -notmatch "urlpatterns\s*=\s*\[") {
        throw "urlpatterns not found. Please check mysite/urls.py."
    }

    $route = "urlpatterns = [`r`n    path('cities/select/', include('apps.cities.selection_urls')),"
    $urls = [regex]::Replace(
        $urls,
        "urlpatterns\s*=\s*\[",
        $route,
        1
    )

    Save-File $urlPath $urls
}


# 7. CHECK DJANGO AND ADD STARTER CITIES

Write-Host "Checking Django..." -ForegroundColor Cyan

python manage.py check

if ($LASTEXITCODE -ne 0) {
    throw "Django check failed. Fix the errors before continuing."
}

Write-Host "Populating city records..." -ForegroundColor Cyan

python manage.py seed_cities

if ($LASTEXITCODE -ne 0) {
    throw "City seeding failed. Check your database connection."
}

python manage.py shell -c "from django.urls import reverse; print('City URL:', reverse('city_selection'))"

Write-Host ""
Write-Host "City Selection setup completed!" -ForegroundColor Green
Write-Host "Open: http://127.0.0.1:8000/cities/select/"
