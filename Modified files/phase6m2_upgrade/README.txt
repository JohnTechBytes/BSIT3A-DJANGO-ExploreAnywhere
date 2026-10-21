ExploreAnywhere Phase 6M.2 — Corrected Discovery Cleanup Installer
==================================================================

Why Phase 6M.1 failed:
  Django's get_template() expects 'places/_discovery_modes.html' rather
  than 'templates/places/_discovery_modes.html'. Django system checks passed,
  but the incorrect template path made the installer roll back safely.

This version fixes the template validation paths and applies the same targeted
cleanup. It does NOT change models, migrations, business data, MapTiler,
recommendation logic, or Nearby JavaScript.

Cleanup:
 - Remove duplicate Popular Searches below the Discover tabs
 - Remove the long tab explanation
 - Remove the redundant back-to-All-Places link on Near Me
 - Keep the three tabs and the Near Me quick searches by the search box

INSTRUCTIONS — VS Code PowerShell in the ExploreAnywhere project root:

1) Activate your virtual environment if needed:
   .\venv\Scripts\Activate.ps1

2) Extract the downloaded ZIP:
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6M2_Validation_Fix.zip" -DestinationPath ".\phase6m2_upgrade" -Force

3) Dry run (no changes):
   python ".\phase6m2_upgrade\exploreanywhere_phase6m2_validation_fix.py" --dry-run

4) If dry-run passes, install:
   python ".\phase6m2_upgrade\exploreanywhere_phase6m2_validation_fix.py"

5) Validate:
   python manage.py check

The installer automatically backs up original templates under
phase6_backups/phase6m2_discovery_<timestamp>.zip. It runs Django system checks
and compiles templates using the corrected Django-relative names.
On failure it rolls back modified files.

Successful installation prints the exact --restore command to undo changes.
Restart Django if needed and refresh Chrome with Ctrl+Shift+R.

If this version fails, copy/paste the full error rather than manually editing
or bypassing a check.
