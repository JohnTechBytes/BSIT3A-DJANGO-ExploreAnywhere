ExploreAnywhere — Phase 6G.1 Nearby MapTiler Tile Repair
======================================================

Problem:
- Nearby Results Map requests tile.openstreetmap.org tiles and receives HTTP 403.
- Discover Kabankalan uses MapTiler successfully.

Change:
- Modifies ONLY templates/places/nearby_places.html.
- Reuses the existing working MapTiler browser key and raster styles from
  templates/places/attraction_carousel.html at installation time.
- Includes MapTiler and OpenStreetMap attribution and a tile-request error message.
- Preserves existing nearby cards, verified-only filtering, map markers,
  lazy Leaflet loading, distance sorting, links, and DB records.
- No MapTiler key is bundled in this ZIP or printed by the installer.

How to install (VS Code PowerShell, inside Django project folder):
1. .\venv\Scripts\Activate.ps1
2. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6G1_MapTiler_Repair.zip" -DestinationPath ".\phase6g1_upgrade" -Force
3. python ".\phase6g1_upgrade\exploreanywhere_phase6g1_maptiler_repair.py" --dry-run
4. Only if the dry run passes:
   python ".\phase6g1_upgrade\exploreanywhere_phase6g1_maptiler_repair.py"
5. python manage.py check
6. python manage.py makemigrations --check --dry-run
7. Restart Django; hard refresh browser (Ctrl+Shift+R).
8. Browse http://127.0.0.1:8000/places/?mode=nearby and open the Nearby map.

If you downloaded a ZIP with another nesting structure, locate the script:
  Get-ChildItem .\phase6g1_upgrade -Filter exploreanywhere_phase6g1_maptiler_repair.py -Recurse -File | Select-Object -ExpandProperty FullName

Expected result:
- Nearby uses MapTiler streets by default, with satellite/hybrid switcher.
- Existing pins, map popups, Details/Directions remain working.
- Browser DevTools Network should no longer request tile.openstreetmap.org.
- If MapTiler tile requests are blocked, the map status will explain that
  the provider/key/network should be checked. Do not bypass provider restrictions.

Restoration:
- The installer prints the exact --restore command and records the backup
  under phase6_backups/nearby-tiles-...
- Do not edit or overwrite the patched template before restoring.
- Use the exact backup directory printed by the installer.

Safety:
- Installer refuses newer/unexpected source edits.
- Does not change Django views, database, city filters, search, GPS, or map keys.
- On Django validation failure, restores the original Nearby template.
- MapTiler public browser key should be restricted to intended site origins in
  your MapTiler account; use a production origin when deploying in the future.
