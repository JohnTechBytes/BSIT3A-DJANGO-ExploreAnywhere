ExploreAnywhere Phase 6N — Visitor Result Card Polish
==================================================

This installer was made from the uploaded ExploreAnywhere_Phase6N_Source.zip.
The ZIP contains only this README and the Python installer, not your private templates,
MapTiler key, database, photos, or site files.

Changes ONLY:
  templates/places/nearby_places.html
  templates/places/attraction_carousel.html

Improvements:
  - Cleaner photo space and genuine-photo-missing placeholder; no fake destination photos.
  - 640x360 dimension hints; existing lazy loading and async decoding kept.
  - Balanced badges and shorter card summaries.
  - Near Me result cards: two-column Details/Directions, full-width Show on Map.
  - Explore Places cards: clear Details + actual Google Maps directions URL.
  - Thumb-friendly 44px controls, better keyboard focus, reduced-motion support.

Preserved:
  - MapTiler token, styles and Leaflet/map JS
  - Search, recommendation scores, category/hobby filters
  - Nearby distance filters, permitted GPS, optional Kabankalan landmarks
  - Django Admin, publication/verification permissions and database records

RUN THESE COMMANDS from the project ROOT (manage.py must be there):

  .\venv\Scripts\Activate.ps1
  Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6N_Result_Cards.zip" -DestinationPath ".\phase6n_upgrade" -Force
  python ".\phase6n_upgrade\exploreanywhere_phase6n_result_cards.py" --dry-run
  python ".\phase6n_upgrade\exploreanywhere_phase6n_result_cards.py"
  python manage.py check

If the dry run says SOURCE MISMATCH, STOP and send your updated templates.
Do not force the installer or overwrite your newer code.

After install: Restart Django, Ctrl+Shift+R Chrome. Test /places/?browse=all
and /places/?mode=nearby in Chrome and Android (including map card selection).

BACKUPS: Saved in phase6_backups/phase6n_cards_*.zip.
The installer prints a full --restore command upon success.
The installer validates via manage.py check and compiles both correct template names:
  places/nearby_places.html
  places/attraction_carousel.html
On validation failure it automatically restores both original templates.

Important: This package has passed LOCAL fixture tests, but the real Django site
and Android UI must be tested on your device.
