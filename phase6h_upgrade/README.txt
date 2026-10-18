EXPLOREANYWHERE — PHASE 6H: SMART NEARBY DISTANCE FILTER
========================================================

WHAT CHANGES
- Adds a distance filter (1/3/5/10/25 km straight-line) to Nearby results.
- Filter stays disabled until visitor chooses a verified Kabankalan landmark
  or grants GPS permission (GPS stays in the browser).
- Result cards, count, and pins update together; absent coordinates are
  excluded only when a numeric radius is selected.
- The map highlights the selected marker and fits only visible pins.
- Adds quick service searches (Coffee, Restaurant, Barber, Mall, Billiards).

MODIFIED FILE
- templates/places/nearby_places.html ONLY.

NOT CHANGED
- No database, models, migrations, Django search queries, MapTiler key,
  Leaflet asset URLs, or verification/approval logic.
- No GPS coordinates are sent to the backend.
- No unverified OSM candidates are shown.

INSTALLATION (PowerShell, in project folder)
1. .\venv\Scripts\Activate.ps1
2. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6H_Nearby_Distance.zip" -DestinationPath ".\phase6h_upgrade" -Force
3. python ".\phase6h_upgrade\exploreanywhere_phase6h_nearby_distance.py" --dry-run
4. Only if DRY RUN OK: python ".\phase6h_upgrade\exploreanywhere_phase6h_nearby_distance.py"
5. python manage.py check
6. python manage.py makemigrations --check --dry-run
7. Restart Django and hard-refresh Chrome.

TESTS
- Near Me initially shows all currently published, verified results;
  distance dropdown is disabled until a location reference is chosen.
- Choose a verified landmark: distances sort from that point and dropdown enables.
- Choose 3 km: cards, count, and map pins narrow consistently.
- Choose 1 km with no matches: clear empty state, reset makes all reappear.
- Change to 10 km: more places may appear; missing-coordinate listings excluded.
- Clear distance: all matching places return, even without recorded coordinates.
- Use GPS (HTTPS/localhost browser): radius filters operate client-side.
- Exact name, service-category search, Details, Directions, MapTiler styles work.
- Android has no horizontal overflow.

RESTORE
The installer prints an exact restore command and preserves backup bytes
in phase6_backups/nearby-radius-...  Restoration refuses to overwrite
unrelated later edits.

NOTE
This is a client-side radius filter on the currently displayed results,
not a server-side global nearest-neighbor search. Existing MAX_RESULTS=250
still applies. Distances are straight-line approximations, not travel times.
