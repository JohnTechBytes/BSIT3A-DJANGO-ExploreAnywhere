ExploreAnywhere Phase 5D.1 — Django Admin Sidebar and Dashboard UI
==================================================================

SCOPE
- Modern desktop left sidebar; mobile menu drawer; streamlined overview cards.
- Key links: Destinations, Visit approvals, Users, City information.
- "Other permitted modules" holds less-used admin model links. Nothing is deregistered.
- Dashboard metrics are queried read-only and visible only with matching staff permissions.
- No fake counts and no modifications to auth, City 2 filtering, PlaceAdmin, VisitCheckInAdmin,
  form checks, site security, migrations or database records.
- Django's Save, Delete, CSRF, permissions, audit History, and approval actions remain available.

INSTALL (in project root, VS Code PowerShell, with working venv activated):

  Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase5D_Admin_UI.zip" -DestinationPath ".\phase5d_upgrade" -Force
  python ".\phase5d_upgrade\exploreanywhere_phase5d_admin_upgrade.py" --dry-run
  python ".\phase5d_upgrade\exploreanywhere_phase5d_admin_upgrade.py"
  python manage.py check
  python manage.py makemigrations --check --dry-run

VERIFY
- Navigate to http://127.0.0.1:8000/admin/ while logged in as a staff user.
- Left navigation and dashboard cards should be visible.
- "Other permitted modules" expands to Django's normal accessible module list.
- Destinations page retains city lock, hobbies, photo credits, verification controls.
- Visits page retains staff-reviewed actions; pending visits are never auto approved.
- Check staff permissions by signing in with a restricted staff test account if available.
- Test mobile menu open, close, Escape and sidebar scroll.

If styling/templates do not appear, check Django's TEMPLATES['DIRS'] includes BASE_DIR / 'templates'.
The installer checks this automatically and restores originals on template-resolution failure.

ROLLBACK
Installer prints an exact --restore command with its timestamped backup directory.
Only unmodified installer-created files are removed. Subsequent manual changes cause a safe stop.

NOTE: Existing admin templates in the destination project are not overwritten. The installer
refuses unexpected files and asks for a merge-aware update instead.
