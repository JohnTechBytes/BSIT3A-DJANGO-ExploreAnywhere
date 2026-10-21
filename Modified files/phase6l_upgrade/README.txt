ExploreAnywhere Phase 6L - Visitor Experience Optimization
=========================================================

What this changes (4 HTML templates only):
- All Places search is front-and-center. Category/hobby/sort filters sit in an optional disclosure, automatically opened when a filter is active.
- Repeated result-count UI and always-visible long recommendation explanations are reduced.
- Near Me does not show two copies of the same category quick searches.
- The long GPS/privacy explanation is available on demand; the short explanation stays visible.
- Home-page hobby cards now launch the existing smart search instead of being non-interactive display cards.
- Mobile tap targets and search input sizing receive small accessibility improvements.

Preserved: Django views, existing search and filters, MapTiler styles/key, pins, GPS, landmarks, ratings, authentication, staff verification, database, saved places, itineraries, visits.

INSTALL FROM YOUR PROJECT FOLDER (VS Code PowerShell):
1) .\venv\Scripts\Activate.ps1
2) Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6L_Visitor_UX.zip" -DestinationPath ".\phase6l_upgrade" -Force
3) python ".\phase6l_upgrade\exploreanywhere_phase6l_visitor_ux.py" --dry-run
4) python ".\phase6l_upgrade\exploreanywhere_phase6l_visitor_ux.py"
5) python manage.py check
6) python manage.py runserver
7) Hard refresh browser using Ctrl+Shift+R.

The script creates a ZIP backup inside phase6_backups. The install validates Django and compiles all four templates, and restores originals on a validation failure. It will refuse to patch files that have already been changed or upgraded. No migration or database write is performed.

MANUAL RESTORE:
python ".\phase6l_upgrade\exploreanywhere_phase6l_visitor_ux.py" --restore ".\phase6_backups\phase6l_visitor_ux_<timestamp>.zip"
(Use your actual backup filename printed during installation.)

TESTS:
- Home: eight interest tiles navigate to the existing search flow.
- All Places: type Amyan Hill; search, then clear search. Open 'More filters', choose a hobby/category, submit; filter remains expanded when active.
- All Places: map view / details / saved places remain available.
- Near Me: only one category shortcut row; chosen service shows active styling; MapTiler, directions, GPS and landmark distance all work.
- Android: search inputs and category chips usable without horizontal overflow.
- Admin: verify 175 unverified businesses remain unpublished; 7 published place records unchanged.

A dry run only confirms compatibility with your source. Real Django/browser behavior must be verified on your laptop.
