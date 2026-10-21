ExploreAnywhere: Kabankalan City Edition
PHASE 5A — EXPLORE PLACES DISCOVERY IMPROVEMENT

BEFORE STARTING
* Keep a separate database backup as normal, although this installer does not touch the DB.
* Run all commands from the VS Code terminal in your Django project root:
  C:\Users\ADMIN\Desktop\BSIT3A-DJANGO-ExploreAnywhere
* Activate your virtual environment if needed.
* The installer updates only apps/places/views.py and
  templates/places/attraction_carousel.html.
* The patch is designed for the four source files uploaded October 17, 2026.
  It refuses to patch if the expected anchors have changed.

POWERSHELL COMMANDS (COPY ONE AT A TIME)

1. Extract the ZIP to a subfolder of your project:
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase5A_Upgrade.zip" -DestinationPath ".\phase5a_upgrade" -Force

2. Check safety without modifying source files:
   python ".\phase5a_upgrade\exploreanywhere_phase5a_discovery_upgrade.py" --dry-run

3. ONLY IF YOU SEE 'DRY RUN OK', install:
   python ".\phase5a_upgrade\exploreanywhere_phase5a_discovery_upgrade.py"

4. Run Django checks:
   python manage.py check
   python manage.py makemigrations --check --dry-run

5. Run your Django development server if it isn't already running:
   python manage.py runserver

6. Open while logged in:
   http://127.0.0.1:8000/places/?browse=all

CHECKLIST
[ ] Browse-all shows all currently active, verified Kabankalan places.
[ ] Searching 'Kabankalan Plaza' shows only Kabankalan Plaza.
[ ] Searching 'nature' shows relevant published destinations.
[ ] Category filter lists real categories assigned to these places.
[ ] Hobby filter lists hobbies assigned to these places.
[ ] Sort Name A-Z changes display order but not recommendation score.
[ ] Highest Rated places with ratings show before unrated places.
[ ] Clear filters/Browse all returns to all published destinations.
[ ] Empty search displays Browse All Destinations link.
[ ] List and Map views and destination details still work.
[ ] Mobile layout works on Android.

NOTES
* Filters and sorting work server-side; no new JavaScript libraries.
* The original Leaflet/MapTiler script is unchanged.
* The original recommendation scoring code is unchanged.
* Existing hobby-search session behavior and Explore Places reset are preserved.
* No migrations, database records, place metadata, or API keys changed.
* A timestamped exact backup of both files is created in phase5_backups.
* If the safety check fails, STOP and send the output: DO NOT force the installer.
* The ZIP contains only source-code installer text and this README.
