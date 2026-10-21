ExploreAnywhere — Phase 5A.2 Discovery Clarity
=============================================

WHAT THIS PACKAGE DOES
- Shows filtered results as "Matching Destinations" and unfiltered results as "Published Destinations".
- Adds removable chips for search, category, hobby and display sort; removal retains other settings.
- Makes one search result a readable wide card on desktop; 2-3 results use a responsive grid; mobile stacks cards.
- Separates search relevance from the personalized score; no change to calculations.
- Where no selected hobbies and no rating signal exist, shows "Not scored yet" and a neutral gray map marker.
- When scoring is available, existing map marker colors remain 80-100 green, 50-79 amber, and 0-49 red.
- Updates popup and legend wording to stress that these are not destination quality ratings.
- Keeps Kabankalan-only filtering, search, ranking, place records, Leaflet and map provider configuration unchanged.
- Does not touch the database or run migrations.

IMPORTANT: PHASE 5A MUST ALREADY BE INSTALLED AND WORKING.
Run these commands from the project root in VS Code PowerShell, one at a time:

  .\venv\Scripts\Activate.ps1
  Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase5A2_Clarity.zip" -DestinationPath ".\phase5a2_upgrade" -Force
  python ".\phase5a2_upgrade\exploreanywhere_phase5a2_clarity_upgrade.py" --dry-run

ONLY IF THE SCRIPT SAYS 'DRY RUN OK', run:

  python ".\phase5a2_upgrade\exploreanywhere_phase5a2_clarity_upgrade.py"
  python manage.py check
  python manage.py makemigrations --check --dry-run

Test in browser:
  http://127.0.0.1:8000/places/?browse=all

Examples:
  - Search "waterfalls": one wide Mag Aso Falls result on desktop.
  - Without hobby selection and ratings, card says "Not scored yet", map marker is gray.
  - With hobby selections but no hobby match, score can be 0%; explanatory text is included.
  - Category/Hobby/Sort chips can each be removed without clearing other settings.
  - Clear All resets query/filters/sort, while preserving personal hobby preferences.
  - Map View works and map provider settings are untouched.
  - Android phone widths: no overflow and one-column card layout.

BACKUP AND RESTORE
The installer saves byte-exact files before changing them in phase5_backups/clarity-<timestamp>/.
If you need to undo Phase 5A.2, use the exact backup directory printed by the installer:

  python ".\phase5a2_upgrade\exploreanywhere_phase5a2_clarity_upgrade.py" --restore ".\phase5_backups\clarity-<timestamp>"

Restore overwrites ONLY apps/places/views.py and templates/places/attraction_carousel.html.
Do not restore if you have since made additional changes to these files without first backing them up.

If the safety check stops, don't force the installer. Send ChatGPT its output and upload
an updated ZIP of the two files. Do not reinstall Django, redo migrations, or change the database.
