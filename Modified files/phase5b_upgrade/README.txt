ExploreAnywhere: Kabankalan City Edition
PHASE 5B — DESTINATION DETAILS UI/UX
======================================

This patch was based on the six source files uploaded Oct 17, 2026.
Changes only:
  apps/places/views.py            — add hobbies to Place Details prefetch
  templates/places/place_detail.html — modern responsive visual layout

UNCHANGED: recommendations, existing URL endpoints, model fields, data,
migrations, media storage, visit approval rules, Django settings, map keys.

1) Extract the entire ZIP to your ExploreAnywhere project directory.
2) Run from the project root in VS Code PowerShell:
   .\venv\Scripts\Activate.ps1
   python .\phase5b_upgrade\exploreanywhere_phase5b_detail_upgrade.py --dry-run
3) Only if DRY RUN OK:
   python .\phase5b_upgrade\exploreanywhere_phase5b_detail_upgrade.py
4) Verify:
   python manage.py check
   python manage.py makemigrations --check --dry-run
5) Test as a logged-in visitor:
   - Open Amyan Hill (image may be pending). Use Save, Itinerary, Review and Visit actions.
   - Open CPSU Museum (cover photo present during last audit). Click hero to enlarge.
   - Open Kabankalan Plaza (missing verified map coords). See honest empty state.
   - Click nearby destinations, verify only Kabankalan approved places.
   - Test on Android over your hotspot network and on desktop.
   - Check photo attribution and gallery click-to-enlarge, if actual gallery images exist.

Backup is automatically stored at phase5_backups/detail-ui-<timestamp>.
The success message prints an exact RESTORE command. Restore will refuse to
overwrite files you have changed since the install.

IMPORTANT: The review and visit forms preserve existing semantics; reviews do
not prove physical visits. Some Kabankalan records still lack real photos,
verified opening hours, descriptions or map coordinates. Never fabricate them.

If DRY RUN reports source mismatch, do not force the patch. Re-upload your current
views.py and place_detail.html for a compatibility revision.
