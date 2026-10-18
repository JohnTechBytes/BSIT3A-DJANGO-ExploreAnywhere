ExploreAnywhere — Phase 6B Overpass Endpoint Fix
==============================================
What changes: only apps/places/management/commands/discover_kabankalan_businesses.py
Default endpoint: https://overpass.kumi.systems/api/interpreter
Optional --overpass-endpoint allows switching between the two known HTTPS services.
The installer performs no network queries, DB writes or migrations. Business fetch mode remains a preview only.

Extract this ZIP into .\phase6b_endpoint_fix inside the ExploreAnywhere project.
Run in VS Code PowerShell:
  .\venv\Scripts\Activate.ps1
  python .\phase6b_endpoint_fix\exploreanywhere_phase6b_endpoint_fix.py --dry-run
  python .\phase6b_endpoint_fix\exploreanywhere_phase6b_endpoint_fix.py
  python manage.py check
  python manage.py discover_kabankalan_businesses

This last command makes TWO Overpass POST requests (boundary discovery, then businesses)
with a brief gap. The test GET status=200 does NOT guarantee these POST queries will work.
If fetching fails again, do not poll repeatedly. Save the error and share it for diagnosis.
Do not run --import-snapshot unless the saved preview has been checked and --dry-run succeeds.
Only confirmed businesses should be published after staff review; OSM records are not verified.

For restoration, run the exact --restore command printed by the installer.
