# ExploreKabankalan — Kabankalan City

A Django web system for exploring **Kabankalan City, Negros Occidental**: a
hobby-weighted place directory, natural-language search, a Leaflet map with
live GPS, reviews, itineraries, visit tracking and a customized administrative
panel, backed by locally imported OpenStreetMap and PSGC data.

> **Documentation note.** This document states what the system does today. A
> feature that is only partly built, or that is planned but not yet written, is
> labelled as such in the *Implementation Status* table. Where the project
> title refers to an "AI-assisted" system, the note under *Background of the
> Project* explains exactly which part of that is implemented.

---

## INTRODUCTION

### Background of the Project

Kabankalan City is one of the major cities of Negros Occidental, with a growing
number of restaurants, recreation centers, sports venues, cafes, parks, and
other establishments that serve its residents and visitors. However,
information about these places is scattered across social media pages, word of
mouth, and separate online listings. Residents, newcomers, and visitors who
want to find a place that fits their interests, such as billiards, badminton,
coffee, or nature walks, must search through many sources, and the information
they find may be incomplete, outdated, or not tied to where they currently are.

General-purpose map and review platforms list places, but they do not match
places to a person's hobbies, and they are not designed around the information
needs of a specific city. Local business owners also have limited means to keep
their listings accurate, while city offices have no single platform for sharing
official city information.

To address this need, **Explore Kabankalan** was developed as a web-based,
single-city system built with the Django framework. A visitor can browse the
verified, published places of Kabankalan, filter them by category and hobby,
search in natural language, view results on an interactive map, sort and filter
nearby places by straight-line distance from the device's GPS position or from a
chosen city landmark, read and write reviews, save places, build itineraries,
and track visits on a personal dashboard called **My Journey**. City staff
manage the same records through a customized administrative panel that includes
an OpenStreetMap review queue, so unverified imports never reach the public
directory.

The recommendation engine is **deterministic and rule-based**, not
machine-learning-based. It ranks places by hobby fit (60% weight) and average
rating (20% weight, applied only where reviews exist). Missing signals are
excluded from the denominator rather than treated as zero. Distance is not part
of the ranking score; it is used by the Nearby view for sorting and filtering.

> **Implementation status of "AI-assisted".** The project title names an
> AI-assisted recommendation system. The build in this repository implements
> the recommender as the rule-based scoring function in
> `apps/places/recommendations.py`, and the natural-language search as the local
> intent-and-keyword parser in `apps/places/views.py`. No Anthropic Claude API
> call exists in the codebase. The Claude API layer is specified as the next
> enhancement, and the local parser it would fall back to is already
> implemented and is what the system uses today.

### Statement of the Problem or Project Objectives

The main objective of this project is to design, develop, and evaluate a
web-based, hobby-based place recommendation and city information system for
Kabankalan City that will help users find places that match their interests.

Specifically, the project accomplishes the following technical objectives:

1. **Hobby-based recommendation module.** Allow visitors to filter the place
   directory by hobby and rank the matching places by hobby fit and average
   rating, using a transparent, rule-based scoring function.
2. **Natural-language search.** Interpret queries such as "coffee shops",
   "mag aso falls" or "places in Kabankalan" with a local intent-and-keyword
   parser, ignoring filler words and recognizing named places. The optional
   Claude API interpretation layer is specified as the next enhancement; the
   local parser that it would fall back to is already in use.
3. **Interactive map and nearby search.** Integrate Leaflet with tiles built
   from OpenStreetMap data, live GPS positioning in the browser, in-browser
   distance filtering and sorting, place details, and a landmark reference for
   visitors who decline location access.
4. **Places directory with reviews.** Present verified, published Kabankalan
   places with descriptions, categories, hobbies, coordinates, photos and
   visitor ratings, with one review per user per place.
5. **Itinerary builder.** Let visitors create trips, add stops from the
   directory, set arrival times, reorder or remove stops, and delete trips.
   Stops are chosen manually; the system does not generate suggested
   itineraries.
6. **My Journey dashboard.** Organize a visitor's saved places, itinerary
   plans, reviews and verified visit check-ins in one page, with visit points
   and badges.
7. **Administrative panel and data import.** Provide city administrators and
   staff with a customized Django admin for place listings, verification,
   photo management, bulk publication actions, visit moderation, a business
   review queue for OSM imports, and city information records, together with
   management commands that import PSGC codes, an OSM extract and Wikimedia
   imagery.
8. **Role-based access control.** Define the four roles required by the system
   (user, business owner, city administrator, system administrator) on a custom
   user model, and enforce access through Django's staff, superuser and model
   permissions so that administrative screens are restricted to authorized
   accounts.
9. **Evaluation instruments.** Build the System Usability Scale (SUS)
   instrument and a recommendation-relevance instrument into the system's data
   model, including the standard 0–100 SUS scoring, so that a usability
   evaluation can be administered with residents, visitors, and city or
   business representatives.

### Significance of the Project

The system provides practical value to the following beneficiaries:

- **Residents and Visitors.** Find places that match their hobbies, see
  distance, details and maps in one platform, plan outings through itineraries,
  save places for later, and keep their reviews and verified visits together on
  the My Journey dashboard.
- **Local Business Owners.** Gain visibility through verified, published
  listings whose details can be corrected by city staff. A self-service
  interface for owners to edit their own listings is identified as future work.
- **City Administrators and Tourism Personnel.** Have a central panel for
  verifying and publishing place listings, reviewing imported OSM records
  before publication, moderating visit evidence, and maintaining city
  information records.
- **Future Researchers and Students.** Have a working reference for a
  single-city, hobby-weighted recommender built on Django, including its data
  model, import pipeline, administrative workflow and automated test suite.

### Alignment with Institutional Research Agenda and Sustainable Development Goals

**Institutional Research Agenda Alignment.** The project aligns with the
Institutional IT research priority by applying web technologies to improve
access to local information and services, and by documenting a reproducible
development and verification process.

**Sustainable Development Goal Alignment.**

- **SDG 9 (Industry, Innovation, and Infrastructure):** contributes through
  the use of open data (OpenStreetMap, PSA PSGC) and open web technology to
  build a local information infrastructure for one city.
- **SDG 11 (Sustainable Cities and Communities):** contributes by improving
  residents' and visitors' access to city information, public spaces, and
  recreational places.

---

## SCOPE AND LIMITATIONS

### System Scope and Technical Architecture

| Component | Description and Coverage |
|---|---|
| **Setting and Coverage** | Kabankalan City, Negros Occidental only. `KabankalanOnlyMiddleware` pins every session to Kabankalan (city pk 2), and the public and administrative querysets filter to that city. Places, information, users and evaluation activities are limited to Kabankalan. |
| **Accounts and Roles** | Custom user model with the four roles required by the system — user, business owner, city administrator, system administrator — plus a managed-city field, avatar, bio and coordinates. Registration creates a `user`. Administrative access is governed by Django's staff, superuser and model permissions. |
| **Kabankalan City Information** | `CityInformation` records (title, type, description, thumbnail, display order) are maintained through the administrative panel. The public City Information page is **not enabled in this build**; the legacy information routes are disabled in `apps/info/urls.py`. |
| **Hobbies and Hobby Selection** | Hobbies are attached to places. Visitors filter the directory by category and by a single hobby from the search panel, and the chosen hobby is kept for the session. The earlier standalone hobby-selection route now redirects to the place directory. |
| **Places Directory with Details and Map Location** | Verified, published Kabankalan places with category, hobbies, description, address, coordinates, cover photo and gallery. The public listing is a looping carousel with list and map views and a details panel. Cover-photo labels indicate whether an image is set, not whether its usage rights were verified. |
| **Natural-Language Search** | A local intent-and-keyword parser handles queries such as "coffee shops", "mag aso falls" or "places in Kabankalan", ignoring filler words and matching named Kabankalan places. No external AI service is called. |
| **Recommendation Engine** | Deterministic ranking: hobby fit 60%, average rating 20% where reviews exist, with missing signals excluded from the denominator. Results are ordered by score, then by number of matched hobbies, then by title. Match percentages are not displayed to visitors. |
| **Interactive Map** | Leaflet 1.9.4, loaded on demand, with streets, satellite and hybrid layers from MapTiler (built on OpenStreetMap data) and OpenStreetMap/MapTiler attribution. Markers open a title and category popup; selecting a card flies the map to the place. |
| **Nearby Search and Live GPS** | The Nearby view reads the browser's geolocation, computes straight-line distance to each place, and filters or sorts results by distance (any distance, 1, 3, 5, 10 or 25 km). A curated Kabankalan landmark can serve as the reference point when GPS is unavailable or declined. Distances are straight-line estimates, not driving routes or travel times. |
| **Reviews and Ratings** | One review per user per place, 1–5 stars plus an optional comment; reviews can be updated or deleted; the average rating feeds both the place page and the recommender. Reviews are opinions and do not by themselves prove an in-person visit. |
| **Saved Places** | Visitors save and unsave places; saved places appear on a dedicated page and on the My Journey dashboard. |
| **Itinerary Builder** | Trips with a title and day number. Stops can be added from the directory, time-stamped, reordered and removed, and trips can be deleted. Itinerary suggestions are not generated by the system. |
| **My Journey Dashboard** | One page aggregating saved places, itinerary plans, the visitor's reviews and visit check-ins, with visit points and badges. Hobby selections and search history are not displayed. |
| **Visit Check-ins and Rewards** | A visitor reports a visit with a date and a corroborating note. Staff approve or reject the check-in in the administrative panel; only approved visits count toward points and badges. |
| **Administrative Panel** | Customized Django admin with destination management (search, category/verification/publication filters), bulk publication actions, per-place verification, photo actions, a business review queue for OSM imports, visit moderation, city information records, and the evaluation records. Native Django permissions and safeguards are preserved. |
| **Data Import** | Management commands import PSA PSGC codes, an OpenStreetMap extract and Wikimedia imagery, and enrich, categorize or attach photos to imported places. |
| **Evaluation Instruments** | `SusResponse` stores the ten standard SUS items and computes the 0–100 score; `RecommendationRating` stores relevant, partially relevant or irrelevant ratings for a query and place. Both are managed through the administrative panel; a respondent-facing survey page is not yet built. |
| **Technology Stack** | Python 3 and Django 5.2.18 for the server; MySQL for storage, accessed through the PyMySQL driver; HTML5, CSS3 and JavaScript with Bootstrap 5.3.3 for the interface; Leaflet 1.9.4 with MapTiler tiles for maps; Pillow for image handling. |
| **Target Users** | Residents, visitors and tourists who look for places that match their hobbies; business owners whose listings appear in the directory; city administrators and tourism personnel who verify and publish places and maintain city information records; and system administrators. |

### Implementation Status

| Module | Status | Notes |
|---|---|---|
| Places directory, carousel, details panel | Implemented | Verified, published places only; the carousel loops through every match (capped at 500 as a guard) |
| Hobby filtering and recommendation engine | Implemented | Rule-based; 60% hobby, 20% rating |
| Natural-language search (local parser) | Implemented | No external service |
| Claude API interpretation layer | Planned | Not present in the codebase |
| Leaflet map, drone fly-to | Implemented | Needs a network connection and a MapTiler key |
| Nearby search, live GPS, radius filter | Implemented | Straight-line distance |
| Reviews and ratings | Implemented | One review per user per place |
| Saved places | Implemented | — |
| Itinerary builder | Implemented | Manual stops only |
| Itinerary suggestions | Planned | Not present |
| My Journey dashboard | Partially implemented | Saved places, trips, reviews and visits; no hobbies or search history |
| Visit check-ins and rewards | Implemented | Staff approval required |
| Administrative panel and OSM review queue | Implemented | Bulk approval refuses unverified OSM imports |
| Data import commands | Implemented | PSGC, OSM extract, Wikimedia imagery |
| City information records | Partially implemented | Admin only; public page disabled |
| Roles and access control | Partially implemented | Four roles defined; enforced through Django permissions; no business-owner portal and no city-level scoping |
| SUS instrument | Partially implemented | Model and scoring built; no survey page |
| Recommendation relevance rating | Partially implemented | Model and admin only; no in-page control |
| Privacy notice and registration consent | Planned | Not present |
| Distance in the ranking score | Planned | Distance is used by the Nearby view only |

### Limitations

- The system covers **Kabankalan City only**. Places, information and evaluation
  involving other cities are not included.
- An **internet connection is required for the interactive map and live GPS**:
  Leaflet is loaded from a CDN and map tiles come from MapTiler. Search and
  recommendation logic run on the server and need no external service.
- Map tiles require a **MapTiler API key**, which is currently embedded in the
  page template and should be moved to server-side configuration before public
  deployment.
- **GPS accuracy depends on the user's device**, and all distances are
  straight-line estimates rather than driving distances or travel times.
- **Recommendation quality depends on the completeness and accuracy of place
  data.** The administrative panel reports missing cover photos and refuses to
  publish unverified imports in bulk for this reason.
- Recommendations and search are implemented with **rule-based logic, not
  machine learning or a language model**. The Claude API layer described in the
  project title is not yet implemented.
- The public **City Information page** is not enabled; records exist in the
  administrative panel only.
- The **SUS survey** and the in-page **recommendation relevance rating** are not
  yet exposed to respondents; only the data models, scoring and admin views
  exist.
- **Business-owner self-service** and **city-level administrative scoping** are
  not implemented.
- A **privacy notice and registration consent step** are not yet present.
- **Online booking, reservations, payment integration, and native mobile
  applications** are excluded from the current development phase.

---

## Technical Reference

### Requirements

- Python 3
- MySQL
- Dependencies from `requirements.txt`: Django 5.2.18, PyMySQL, openpyxl,
  Pillow 13 (`openpyxl` is retained for spreadsheet imports but is not imported
  by the current code)

Django is pinned to 5.2.18 because earlier 5.x releases crash on
`BaseContext.__copy__` under Python 3.13 and later (`'super' object has no
attribute 'dicts'`). `mysite/compat.py` is imported from `mysite/__init__.py` as
a safety net for environments still running an affected Django version.

### Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

mysql -uroot -e "CREATE DATABASE exploreanywhere CHARACTER SET utf8mb4"

python manage.py migrate
python manage.py runserver
```

Database settings come from the environment with development defaults
(`exploreanywhere`, user `root`, no password, `127.0.0.1:3306`, `utf8mb4`).
Set `DJANGO_DB_*` variables to point the project at a real MySQL server.

Virtual environments are gitignored under any name (`venv*`, `.venv/`).

### Project layout

```
manage.py
mysite/      settings, urls, wsgi, compat (Django/Python context-copy shim)
apps/        cities, core, dashboard, evaluation, hobbies, imports, info,
             itineraries, places, reviews, search, users, visits
templates/   Django templates
static/      css, js, images, third-party libraries  (served at /static/)
media/       uploaded images                        (served at /media/)
data/        source datasets, read by management commands
docs/        documentation
```

### Data

`data/` holds source datasets — keep it. These are import inputs, not site
content: the boundary files and OSM extract cover the whole country because the
import commands need them to match Kabankalan records.

| Path | Contents |
|------|----------|
| `data/boundaries/` | geoBoundaries Philippines ADM2/ADM3 |
| `data/osm/` | `philippines-261013.osm.pbf` plus `extracted/`, `matching/`, `validation/` |
| `data/psgc_2026_q3_exploreanywhere.csv` | PSA PSGC place codes |

Loaded through management commands such as:

```bash
python manage.py load_psgc
python manage.py categorize_osm_places
python manage.py import_wikimedia_photos
```

### Environment variables

Optional, read at runtime with safe defaults:

| Variable | Used by |
|----------|---------|
| `DJANGO_SECRET_KEY` | session and token signing; set a real key in production |
| `DJANGO_DEBUG` | debug mode (`1`, `true`, `yes`, `on`); defaults to on for development |
| `DJANGO_ALLOWED_HOSTS` | comma-separated list of host names allowed to serve the site |
| `DJANGO_DB_ENGINE` | database engine, e.g. `django.db.backends.mysql` |
| `DJANGO_DB_NAME` | database name |
| `DJANGO_DB_USER` | database user |
| `DJANGO_DB_PASSWORD` | database password |
| `DJANGO_DB_HOST` | database host |
| `DJANGO_DB_PORT` | database port |
| `MAPTILER_API_KEY` | access token for the MapTiler map tiles |
| `EXPLOREANYWHERE_PHOTO_USER_AGENT` | photo discovery commands |
| `WIKIMEDIA_USER_AGENT` | Wikimedia photo lookup commands |

`.env` is not tracked by git; export these in your shell instead.

### Tests

```bash
python manage.py test          # Django runner
pytest                         # pytest.ini points at mysite.settings
```

The suite covers the public flows (search, filters, save/unsave, reviews,
itineraries, check-ins, nearby) and the administrative screens. Fifteen tests
for the retired legacy city-information CRUD routes are skipped: those routes
are disabled, and the tests are kept as the specification for the City
Information module.

### Documentation

- `docs/QUICK_REFERENCE.md` — day-to-day commands and troubleshooting
- `docs/PHASE6P_OPTIMIZATION_GUIDE.md` — photo discovery setup
- `docs/PHASE7_FEATURES_PLAN.md` — feature roadmap
