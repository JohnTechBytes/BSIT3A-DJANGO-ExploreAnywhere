# ExploreKabankalan — Kabankalan City

A Django app for exploring **Kabankalan City, Negros Occidental**: attractions,
reviews, visits, itineraries and a personal journey dashboard, backed by
locally imported OSM and PSGC data.

The site is single-city by design. `KabankalanOnlyMiddleware` pins every
session to Kabankalan (city pk 2), and place detail, nearby search and
discovery all filter to that city — other cities are not browsable.

## Requirements

- Python 3
- MySQL
- Dependencies from `requirements.txt` (Django 5.0.14, mysqlclient, openpyxl)

> A few management commands also import Pillow, requests and pyosmium, which
> are not in `requirements.txt` yet. Install them if such a command fails on
> import.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

mysql -uroot -e "CREATE DATABASE exploreanywhere CHARACTER SET utf8mb4"

python manage.py migrate
python manage.py runserver
```

Database settings are hardcoded in `mysite/settings.py`: database
`exploreanywhere`, user `root`, no password, `127.0.0.1:3306`, `utf8mb4`.

Virtual environments are gitignored under any name (`venv*`, `.venv/`).

## Project layout

```
manage.py
mysite/      settings, urls, wsgi
apps/        cities, core, dashboard, evaluation, hobbies, imports, info,
             itineraries, places, reviews, search, users, visits
templates/   Django templates
static/      css, js, images, third-party libraries  (served at /static/)
media/       uploaded images                        (served at /media/)
data/        source datasets, read by management commands
docs/        documentation
```

## Data

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

## Environment variables

Optional, read at runtime with safe defaults:

| Variable | Used by |
|----------|---------|
| `EXPLOREANYWHERE_PHOTO_USER_AGENT` | photo discovery commands |
| `WIKIMEDIA_USER_AGENT` | Wikimedia photo lookup commands |

`.env` is not tracked by git; export these in your shell instead.

## Tests

```bash
pytest
```

`pytest.ini` points pytest at `mysite.settings` and picks up the per-app
`tests.py` files.

## Documentation

- `docs/QUICK_REFERENCE.md` — day-to-day commands and troubleshooting
- `docs/PHASE6P_OPTIMIZATION_GUIDE.md` — photo discovery setup
- `docs/PHASE7_FEATURES_PLAN.md` — feature roadmap
