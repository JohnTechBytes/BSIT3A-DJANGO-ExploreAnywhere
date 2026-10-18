ExploreAnywhere Phase 6J — Safer Business Review

Install from Django project root (where manage.py exists):

  .\venv\Scripts\Activate.ps1
  Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6J_Business_Review_Upgrade.zip" -DestinationPath ".\phase6j_upgrade" -Force
  python ".\phase6j_upgrade\exploreanywhere_phase6j_business_review.py" --dry-run
  python ".\phase6j_upgrade\exploreanywhere_phase6j_business_review.py"
  python manage.py check

Updates ONLY apps/places/admin.py and templates/admin/places/place/osm_review.html.
Adds matching-record count, clear filters, missing-coordinates filter, human-only possible duplicate warnings, and checklist.
No migrations, no database writes, no changes to verification rules or publication.
Auto-backups to phase6_backups/phase6j-review-... and automatically rolls back if the Django checks fail.
Restore manually: python ".\phase6j_upgrade\exploreanywhere_phase6j_business_review.py" --restore "<backup folder printed by installer>"

The installer intentionally refuses to patch source changed since the supplied ZIP.
Review duplicates independently. Never bulk-approve imported OSM candidates.
