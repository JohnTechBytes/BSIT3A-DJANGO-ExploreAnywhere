ExploreAnywhere Phase 6M.1 — Compatibility Repair
==============================================

Fixes Phase 6M's dry-run failure:
  expected one matching source block, found 0

Why: original Phase 6M matched an exact navigation explanation string.
This version checks recognizable element structure instead and supports both
original Phase 6F/6K markup and Phase 6L-modified markup. It rejects unfamiliar
category sections rather than guessing and never modifies the database.

Removes:
- Redundant Popular searches row in shared Discover navigation
- Long tab explanation below All Places / Near Me / Map View tabs
- Redundant '← All Places' link at the top of Nearby Discovery

Preserves:
- All Places / Near Me / Map View tabs
- Quick searches in the Nearby main search panel
- MapTiler, GPS, landmark fallback, radius filters, recommendations
- Django models, database records, admin verification safeguards

INSTALLATION (VS Code PowerShell, project root with manage.py)
--------------------------------------------------------------
1) Activate virtual environment if needed:
   .\venv\Scripts\Activate.ps1

2) Extract ZIP from Downloads:
   Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6M1_Cleanup_Fix.zip" -DestinationPath ".\phase6m1_upgrade" -Force

3) Dry run (read-only):
   python ".\phase6m1_upgrade\exploreanywhere_phase6m1_cleanup_fix.py" --dry-run

4) On DRY RUN OK, install:
   python ".\phase6m1_upgrade\exploreanywhere_phase6m1_cleanup_fix.py"

5) Confirm Django and refresh your browser:
   python manage.py check
   Ctrl+Shift+R

The installer backs up BOTH original templates to phase6_backups/phase6m1_discovery_*.zip.
It validates Django system checks and template compilation. If validation fails,
it restores both original templates. After successful installation, restore by
running the exact --restore command printed by the installer.

If the dry run still fails, DO NOT bypass the check or manually edit code.
Send the following two current templates for inspection:
  templates/places/_discovery_modes.html
  templates/places/nearby_places.html
