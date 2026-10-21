ExploreAnywhere Phase 6O.6: frontend attribution patch

Changed templates:
  templates/places/nearby_places.html
  templates/places/attraction_carousel.html
  templates/places/saved_places.html

Already display source and license links, so unchanged:
  templates/places/place_detail.html
  templates/places/city_discover.html

Safety:
- This archive modifies templates only, not MySQL, models, migrations, original CSVs, or management commands.
- MANIFEST.json includes SHA256 of the exact uploaded originals and patched files.
- Before copying, verify your local template SHA256 hashes match the originals. Refuse installation if any mismatch; don't overwrite work done since upload.
- Back up the three originals before replacing them.
- After copying, run: python manage.py check
- Parse templates with: python manage.py shell -c "from django.template.loader import get_template; [get_template('places/'+n) for n in ('nearby_places.html','attraction_carousel.html','saved_places.html')]; print('Template parse OK')"
- Preview only: python manage.py phase6o_business_photos --apply-approved --dry-run
- Do NOT execute --confirm-reviewed until after frontend review and final explicit confirmation.

INSTALL (Windows PowerShell, while you are in your Django project):
  1. Download ExploreAnywhere_Phase6O6_Attribution_Patch.zip into your Downloads folder.
  2. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6O6_Attribution_Patch.zip" -DestinationPath ".\phase6o_frontend_staging" -Force
  3. Open and inspect .\phase6o_frontend_staging\apply_patch.ps1
  4. & .\phase6o_frontend_staging\apply_patch.ps1 -ProjectRoot (Get-Location).Path
  5. Run the Django checks shown above.

If Windows execution policy blocks the trusted installer, copy its PowerShell source into your terminal after review, or launch it in a one-time PowerShell process with a suitable execution policy.

The installer verifies SHA256 for the three exact originals and three patched files before making copies. If any original file changed since you uploaded the ZIP, installation stops. It creates timestamped backups and restores them if a copy fails.
