ExploreAnywhere Phase 5D.3 — Admin Final Polish
===============================================
Targets the Phase 5D.2 installation shown in your screenshot.

IMPROVEMENTS
- Dashboard is highlighted ONLY on the dashboard; Destinations, Visit Approvals,
  City Information, and Users show the selected state on their own pages.
- On Destinations, Django's permission-aware Add Place action is rendered next to
  the Destination Management heading; the duplicate top-right slot is removed.
- More compact desktop header and breadcrumbs, while keeping breadcrumbs on edit pages.

PRESERVED
- Django's built-in add/change/delete permissions, staff authentication, CSRF,
  existing admin forms, all approved visit rules, filters and bulk actions.
- No database, source models, image/photo metadata, migrations or city records changed.

HOW TO INSTALL (VS Code PowerShell, project folder with manage.py)
1. .\venv\Scripts\Activate.ps1
2. python ".\phase5d3_upgrade\exploreanywhere_phase5d3_admin_polish.py" --dry-run
3. python ".\phase5d3_upgrade\exploreanywhere_phase5d3_admin_polish.py"
4. python manage.py check
5. Restart the Django server and refresh http://127.0.0.1:8000/admin/.

If --dry-run reports source mismatch, stop and send the output; don't force it.
The installer saves a timestamped backup under phase5_backups and prints a
--restore command for exactly that backup. Restoration refuses if you changed
one of the installed Admin template files afterward, to avoid data loss.

IMPORTANT QA
- Dashboard highlights only Dashboard.
- Destinations list and edit form highlight only Destinations.
- Add Place is beside the destination heading, visible only to authorized staff.
- Search, filters, destination edits, approval actions still function.
- Android sidebar still opens/closes; no horizontal overflow.

A Django system check does not prove complete browser behavior. Verify the UI.
