ExploreAnywhere Phase 6B.4 — Optional bounded Overpass query with city polygon verification

Problem: Nominatim finds Kabankalan relation 3740502, while Overpass city-area
requests repeatedly return HTTP 500. The alternative query mode avoids the
relation(...);map_to_area step, while enforcing the actual administrative polygon
locally. No automatic publication, ever.

Requirements: Phase 6B.3 installed, Django virtual environment active,
trusted internet connection, and current ExploreAnywhere project root.

1) Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6B4_BBox_Fallback.zip" -DestinationPath ".\phase6b4_upgrade" -Force
2) python ".\phase6b4_upgrade\exploreanywhere_phase6b4_bbox_fallback.py" --dry-run
3) python ".\phase6b4_upgrade\exploreanywhere_phase6b4_bbox_fallback.py"
4) python manage.py check
5) python manage.py discover_kabankalan_businesses --query-mode bbox --probe-bbox
6) ONLY IF THE PROBE SUCCEEDS:
   python manage.py discover_kabankalan_businesses --query-mode bbox --category coffee

The probe runs one Nominatim geometry lookup and one SMALL Overpass query around
the middle of Kabankalan's bounding box. It does not create a snapshot or DB rows.
If that succeeds but the full coffee request fails with HTTP 500, stop and share
its error rather than repeatedly polling Overpass. A successful full preview
saves a JSON file but does not import anything into the database.

The entire city bbox may include nearby municipalities. For full preview requests,
the importer filters candidates through Kabankalan's actual OSM administrative
polygon before writing the preview. Distances are not computed here.

The fallback preserves the original --query-mode area and all existing staging
rules. All candidate businesses remain inactive and unverified when imported
using the separate explicit --import-snapshot command. Do not publish without
staff verification. OpenStreetMap data: © OpenStreetMap contributors, ODbL.

Restore command is printed by the installer on successful installation.
