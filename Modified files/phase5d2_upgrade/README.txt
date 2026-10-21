EXPLOREANYWHERE PHASE 5D.2 — DESTINATION ADMIN CLEANUP
=====================================================
Based on the source you uploaded (ExploreAnywhere_Phase5D2_Admin_Source.zip).

This package updates ONLY:
  apps/places/admin.py
  templates/admin/base_site.html
  templates/admin/index.html
  templates/admin/places/place/change_list.html (created by installer)

WHAT CHANGES
- Clean destination list with an aligned search + category + verification + activity toolbar.
- Category choices use only actual categories from existing Kabankalan destination records.
- Destination names show hobbies beneath them; photo and map column labels are readable.
- Row checkboxes continue to enable the original bulk publication actions.
- Dashboard header is less repetitive; sidebar prioritizes Destinations and shows active section.
- Main sidebar links no longer appear a second time in 'Other permitted modules'.

WHAT DOES NOT CHANGE
- Database records and migrations; admin roles, permissions or staff approval actions.
- Photo and coordinate verification rules; existing place forms and content records.
- Map keys, visitor routes, personalized recommendations, search outside admin.

HOW TO INSTALL
Open the ExploreAnywhere folder containing manage.py in VS Code PowerShell.
Activate .\venv\Scripts\Activate.ps1
Extract ZIP to .\phase5d2_upgrade
Then run:
 python .\phase5d2_upgrade\exploreanywhere_phase5d2_admin_cleanup.py --dry-run
 python .\phase5d2_upgrade\exploreanywhere_phase5d2_admin_cleanup.py
 python manage.py check
Restart the server completely and visit http://127.0.0.1:8000/admin/places/place/

BACKUP AND RESTORE
Installer saves original files to phase5_backups/destination-admin-cleanup-.../
It prints the exact --restore command. That command refuses to erase later edits.
If validation fails, the installer restores the originals automatically.

TESTS
1. Admin Dashboard loads with sidebar.
2. Destination list displays seven Kabankalan places (if publication hasn't changed).
3. Search and filter by category, verified status and active status work.
4. Clear filters restores all destinations.
5. Bulk actions only appear after selecting a row; publishing/unpublishing permissions remain.
6. Destination editing preserves genuine photo attribution and map coordinate checks.
7. The admin remains usable on phone screens.

NOTE: Source compatibility and syntax were tested when packaging. Real Django rendering
and interaction must be verified locally. No installer can guarantee dynamic behavior
from static code alone.
