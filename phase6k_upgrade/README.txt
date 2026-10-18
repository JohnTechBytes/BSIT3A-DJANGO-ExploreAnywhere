ExploreAnywhere Phase 6K — Kabankalan Landmark Selector Simplification
==================================================================

WHAT IT CHANGES
- GPS remains the main Nearby distance reference.
- A collapsible "Can't use GPS?" section offers a small Kabankalan-only landmark list.
- The only names allowed are already published, reviewed Kabankalan destinations:
  Kabankalan Plaza, CPSU Museum, Mag Aso Falls, Amyan Hill,
  Maronggues Hill, Mount Luyang, Mount Nai-guin.
- Only currently published, verified records WITH map coordinates will appear.
- Kabankalan Plaza will not appear if it still lacks approved coordinates.
- A manually supplied origin ID outside this curated list is ignored.
- Search, quick categories, Phase 6H distance radius, GPS, and results-map pins remain intact.
- No citywide geofencing of the visitor's GPS (existing behavior remains unchanged).

INSTALLATION — from Django project folder in VS Code PowerShell
1) .\venv\Scripts\Activate.ps1
2) Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6K_Kabankalan_Landmarks.zip" -DestinationPath ".\phase6k_upgrade" -Force
3) python ".\phase6k_upgrade\exploreanywhere_phase6k_kabankalan_landmarks.py" --dry-run
4) If DRY RUN OK:
   python ".\phase6k_upgrade\exploreanywhere_phase6k_kabankalan_landmarks.py"
5) python manage.py check
6) Restart python manage.py runserver, hard refresh browser.

SOURCE COMPATIBILITY
- Installer targets the Phase 6H Nearby distance filters + Phase 6I hobby removal
  and the unmodified Phase 6H source version of apps/places/nearby.py.
- If a source-mismatch warning occurs, NOTHING is changed. Send your current
  nearby.py and nearby_places.html for a revised installer.

BACKUPS / ROLLBACK
- Both files are copied into phase6_backups/phase6k-landmarks-<timestamp>/
- The installer runs Django system and template checks; on failure, it restores
  both original files automatically.
- To restore manually, copy the printed --restore command and backup path,
  or use:
  python .\phase6k_upgrade\exploreanywhere_phase6k_kabankalan_landmarks.py --restore "phase6_backups\phase6k-landmarks-YYYYMMDD-HHMMSS-ffffff"
- Manual restore refuses to overwrite newer source edits.

SECURITY
- Does not access or change database records, migrations, settings or keys.
- Does not include MapTiler key or full template content.
- Preserves active+verified Kabankalan filtering.
- GPS coordinates remain in browser and are not sent to Django.

TEST IN BROWSER
- /places/?mode=nearby: Use my location remains primary.
- Open "Can't use GPS?" and confirm only curated Kabankalan references appear.
- A landmark without confirmed coordinates (e.g. Kabankalan Plaza in shared state)
  must NOT appear until updated with genuine verified coordinates.
- Choose a landmark; the page should sort and enable 1/3/5/10/25 km filters.
- Toggle Map; confirm pins match the visible results.
- Verify Android responsive controls, view details/directions, published-only listings.

NOTE: The installer was tested on a reconstructed source snapshot, not the
running Windows/Django database. Actual system validation runs during install.
