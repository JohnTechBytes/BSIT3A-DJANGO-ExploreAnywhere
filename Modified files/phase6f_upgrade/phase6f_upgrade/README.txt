EXPLOREANYWHERE PHASE 6F — UNIFIED DISCOVER KABANKALAN
======================================================

PURPOSE
-------
Unify the existing Browse and Smart Nearby Places interfaces under ONE route:
  /places/?browse=all                 -> All Places (hobby recommendations)
  /places/?mode=nearby                -> Near Me (verified businesses + location)
  /places/?browse=all&display=map     -> Map View (existing Leaflet map)

Search terms such as "coffee shop near me" route to Near Me.
Named destinations such as "Kabankalan Plaza" retain the existing search.
An existing public business named "Coffee & Talk" is matched exactly in Near Me.
Original /places/nearby/ links remain supported through a redirect.

The update keeps these workflows and protections unchanged:
* Active + independently verified + Kabankalan-only results
* Hidden/unverified OSM imports stay hidden
* Personalized recommendation formula and ranking
* Existing map provider, Leaflet on-demand loading, popups and score colors
* Browser-only GPS processing, landmark fallback, straight-line distances
* Saved Places, itineraries, reviews, visits, and Django Admin
* Existing database, models, migrations and records

INSTALL — RUN FROM YOUR PROJECT FOLDER (VS CODE POWERSHELL)
---------------------------------------------------------
1. Activate your existing environment:
     .\venv\Scripts\Activate.ps1

2. Extract ZIP downloaded to Downloads:
     Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6F_Unified_Discovery.zip" -DestinationPath ".\phase6f_upgrade" -Force

3. Safety check:
     python ".\phase6f_upgrade\exploreanywhere_phase6f_unified.py" --dry-run

4. If DRY RUN OK, apply:
     python ".\phase6f_upgrade\exploreanywhere_phase6f_unified.py"

5. Verify:
     python manage.py check
     python manage.py makemigrations --check --dry-run

6. Restart Django and open:
     http://127.0.0.1:8000/places/?browse=all

FILES CHANGED
-------------
apps/places/views.py
apps/places/nearby.py
templates/places/attraction_carousel.html
templates/places/nearby_places.html

NEW FILE
--------
templates/places/_discovery_modes.html

If the dry run says the source files are newer than those in the ZIP,
STOP rather than overwriting them. Share the updated source files.

RESTORE
-------
The installer prints a backup folder in phase6_backups and a full --restore
command. For example (replace the path with the exact output):
  python ".\phase6f_upgrade\exploreanywhere_phase6f_unified.py" --restore ".\phase6_backups\unified-YOUR-BACKUP"

MANUAL QUALITY ASSURANCE
------------------------
1. All Places tab shows only the published Kabankalan listings.
2. Near Me tab loads business search and accurate verified-only autocomplete.
3. Home search "coffee shop near me" opens /places/?mode=nearby&q=...
4. Browse search "Kabankalan Plaza" returns the correct place.
5. "Coffee & Talk" finds exactly that published business IF independently verified.
6. 175 imported-but-unverified OSM candidates remain hidden publicly.
7. Choose a landmark and check straight-line distance ranking.
8. Map View tab opens original Leaflet map with existing markers and legends.
9. List view still defers the Leaflet library download.
10. Existing /places/nearby/ bookmarks redirect to /places/?mode=nearby.
11. Test Save Place, View Details and mobile layout on Android.

GPS on Android via plain HTTP hotspot generally cannot be accessed.
Use the verified-landmark option. HTTPS can be added later.
