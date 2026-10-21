ExploreAnywhere Phase 6G — On-Demand Nearby Results Map
======================================================

This update changes ONLY templates/places/nearby_places.html.
There are no database migrations and no model, business, import or account changes.

Highlights:
- Nearby search result cards and map pins come from the SAME filtered verified,
  published, Kabankalan-only results. Unreviewed OSM candidates remain invisible.
- 'View nearby results on map' loads Leaflet only when clicked.
- 'Show on map' on a card focuses the matching marker and its Details/Directions.
- Distance labels keep using browser GPS (with consent) or the selected verified
  Kabankalan landmark; coordinates from the visitor are not posted to Django.
- Listings with missing coordinates stay in the results list, but have no pin.
- With zero mappable results the map button explains why it is unavailable.
- The Nearby Results Map uses OpenStreetMap raster tiles and clear OSM attribution;
  the EXISTING Map View MapTiler configuration is unchanged.
- This is a map of matching destinations, NOT a driving-route map or live
  establishment directory. OpenStreetMap business candidates require independent
  verification and publication before they appear.

PowerShell from C:\Users\ADMIN\Desktop\BSIT3A-DJANGO-ExploreAnywhere:

    .\venv\Scripts\Activate.ps1
    Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6G_Nearby_Results_Map.zip" -DestinationPath ".\phase6g_upgrade" -Force
    python ".\phase6g_upgrade\exploreanywhere_phase6g_nearby_map.py" --dry-run
    python ".\phase6g_upgrade\exploreanywhere_phase6g_nearby_map.py"
    python manage.py check
    python manage.py makemigrations --check --dry-run

If the dry run does not say DRY RUN OK, do NOT run the installer; the source
has changed and needs to be reviewed before a new patch can be made.

Restart your Django server and visit:
    http://127.0.0.1:8000/places/?mode=nearby

Browser QA:
  1. List results load without Leaflet requests (Chrome F12 > Network).
  2. Click View nearby results on map: the matching, mapped results appear.
  3. Click Show on map on a result card: marker and popup focus correctly.
  4. Click a map marker; View Details and Directions work.
  5. Select a verified landmark: distance labels change, map reference pin appears.
  6. Filter to missing-coordinate result: no false pin is displayed.
  7. Search cafes (0 verified is fine): no unverified OSM candidates appear.
  8. Test Android portrait/landscape: map and cards should not overflow.

Rollback (the install command prints your exact timestamped backup folder):
    python ".\phase6g_upgrade\exploreanywhere_phase6g_nearby_map.py" --restore "phase6_backups\nearby-results-map-<timestamp>"

Never use a public HTTP development server for production; mobile GPS generally
requires HTTPS. Limit localhost/hotspot testing to a trusted network.
