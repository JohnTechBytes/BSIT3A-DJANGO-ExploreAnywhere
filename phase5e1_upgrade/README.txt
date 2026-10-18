# ExploreAnywhere — Phase 5E.1 On-Demand Map Resources

Target: `templates/places/attraction_carousel.html` ONLY.

Preserves recommendation formula, category/hobby filtering, search, MapTiler key, original Leaflet map styles, markers, score colors, AJAX-free server rendering, login/session flows, destination pages, Admin, and all database records.

## Steps (Windows PowerShell, from your ExploreAnywhere project root)

1. Activate venv: `./venv/Scripts/Activate.ps1`
2. Extract ZIP into `./phase5e1_upgrade`.
3. `python ./phase5e1_upgrade/exploreanywhere_phase5e1_map_on_demand.py --dry-run`
4. Only if dry run passes: `python ./phase5e1_upgrade/exploreanywhere_phase5e1_map_on_demand.py`
5. `python manage.py check` and `python manage.py makemigrations --check --dry-run`.
6. Restart Django, hard-refresh Chrome, test on desktop and Android.

## Behavior to verify

- Open Explore Places in List View; Leaflet CSS/JS should NOT be requested until Map View is opened.
- Open Map View; markers, score legend, three map styles and card details work.
- Click a destination card with coordinates; Map View and focus/zoom work even on first click.
- Open Kabankalan Plaza search (no coordinates); Map View says location unavailable without fetching Leaflet.
- Search/filter/sort/list view and pagination still work; destination image placeholders remain accurate.
- If a CDN fails: map gives an understandable message; clicking Map View retries while destination cards remain accessible.
- Android viewport and controls remain usable.

## Rollback

Installer prints the exact restore command and creates `phase5_backups/map-on-demand-...` containing the unchanged previous template plus a checksummed manifest. `--restore` refuses to overwrite subsequent edits.

## Limits

This is a frontend resource-loading optimization; do not claim a measured speedup without before/after browser Network or Lighthouse measurements. Django `runserver` isn't a production benchmark. Map resources still require an internet connection.
