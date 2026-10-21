EXPLOREANYWHERE — PHASE 6A: SMART NEARBY PLACES

Goal: Recognize billiards, coffee shops, barbershops, restaurants and malls
in natural-language search, suggest ONLY real published verified Kabankalan
records already in your database, and sort matching listings by distance.

IMPORTANT DATA LIMIT: Your prior database audit reported only 7 approved
Kabankalan places. The system will NOT invent billiard halls, barbershops,
restaurants or malls. Such searches show a clear empty state until you add
and verify real establishments in Django Admin, including category, address,
coordinates (if available), images and photo rights.

WHAT IT CHANGES
Existing files:
  apps/places/views.py                        (recognized service search redirects)
  apps/places/urls.py                         (adds two named URLs)
  templates/home.html                         (home search no longer requires hobbies)
  templates/places/attraction_carousel.html   (nearby entry link)
New files:
  apps/places/nearby_intent.py                (service intent & category aliases)
  apps/places/nearby.py                       (Kabankalan-only nearby listings)
  templates/places/nearby_places.html         (responsive local-distance UI)

IT DOES NOT CHANGE: database, migrations, data, your existing hobby ranking,
MapTiler key, main Leaflet map, Staff Admin, reviews, trips or rewards.

INSTALL IN VS CODE POWERSHELL — one line at a time, in project root
  .\venv\Scripts\Activate.ps1
  Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6A_Nearby_Places.zip" -DestinationPath ".\phase6a_upgrade" -Force
  python ".\phase6a_upgrade\exploreanywhere_phase6a_nearby.py" --dry-run
  python ".\phase6a_upgrade\exploreanywhere_phase6a_nearby.py"
  python manage.py check
  python manage.py makemigrations --check --dry-run

DO NOT install if dry run fails. It means your actual project differs from
these uploaded versions. Ask for an updated code-compatible installer.

After installation, restart Django and visit:
  http://127.0.0.1:8000/places/nearby/
  http://127.0.0.1:8000/places/nearby/?q=where+can+i+play+billiards
  http://127.0.0.1:8000/places/?q=coffee+shop+near+me

Search from homepage: recognizing a business routes to Nearby automatically.
Other destination searches still use your existing discovery filters.
Use GPS on HTTPS, or choose a verified landmark on Android hotspot HTTP.
GPS is used in client-side JavaScript and not posted to Django or added to URL.

Distances are straight-line estimates, not routes/driving travel times.
Manual location is a verified landmark reference, NOT claimed live GPS.
Do not claim verified city-boundary membership from GPS. Only listings
in the Kabankalan city record with active+verified flags are shown.
Up to 250 matches are rendered; a warning appears at that bound. Nearby sorting
is across rendered results only and missing-coordinate results remain last.

To restore, copy the --restore command shown after successful installation.
The restorer refuses to overwrite changes made after the installer ran.

QA
1. Home search for "where i can ply billard" opens /places/nearby/
2. Explore Places search for "coffee shop near me" opens /places/nearby/
3. Names: Kabankalan Plaza / Mag Aso Falls still use existing search
4. No verified service listings -> truthful empty state, never fake shops
5. Existing /places/ map, relevance scores and MapTiler continue working
6. 'Use my location' requests permission (HTTPS/localhost) only on click
7. Android hotspot HTTP offers manual landmark sorting, no fake GPS
8. Distances are marked approx straight-line and sort order is ascending
9. Each place has View Details; directions shown only when coords exist
10. Logged-out user cannot access protected nearby page; city scoping retained
11. No migrations; admin continues to work

NEXT PHASE 6B: add verified Kabankalan commercial listings through Admin
or a separately approved source/verification pipeline. Never invent data.
