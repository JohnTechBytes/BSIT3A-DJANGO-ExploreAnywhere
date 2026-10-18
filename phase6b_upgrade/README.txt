ExploreAnywhere Phase 6B — Kabankalan OSM Business Discovery
===========================================================
PURPOSE
Find named OpenStreetMap listings within an OSM administrative-boundary
relation for Kabankalan City. This is SOURCE DISCOVERY, not proof that a
business is real, open, licensed, locally situated, or complete.

Source attribution: © OpenStreetMap contributors, Open Database License (ODbL)
https://www.openstreetmap.org/copyright
Public Overpass endpoints have fair-use limits and can time out.
No guarantee of all businesses or verified facts. No API keys needed.

INSTALL FROM VS CODE POWERSHELL (in ExploreAnywhere project root)
1. .\venv\Scripts\Activate.ps1
2. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6B_OSM_Business_Discovery.zip" -DestinationPath ".\phase6b_upgrade" -Force
3. python ".\phase6b_upgrade\exploreanywhere_phase6b_osm_installer.py" --dry-run
4. python ".\phase6b_upgrade\exploreanywhere_phase6b_osm_installer.py"
5. python manage.py check

DISCOVER (NETWORK ACCESS REQUIRED; DATABASE IS READ-ONLY)
    python manage.py discover_kabankalan_businesses
Prints count and saves a phase6_imports/kabankalan_osm_<timestamp>.json file.
The city boundary is discovered from OSM administrative relations. If the
boundary cannot be found or there are multiple matches, nothing imports.
Use --relation-id NUMBER only after manually verifying the OSM relation.
If Overpass is overloaded (429/504/timeout), wait; avoid frequent retries.

OPTIONAL IMPORT FOR STAFF REVIEW (CREATES UNPUBLISHED RECORDS ONLY)
Select the exact snapshot filename shown by the preview output:
    python manage.py discover_kabankalan_businesses --import-snapshot ".\phase6_imports\kabankalan_osm_YYYYMMDD_HHMMSS.json" --dry-run
    python manage.py discover_kabankalan_businesses --import-snapshot ".\phase6_imports\kabankalan_osm_YYYYMMDD_HHMMSS.json"
Only the second command creates DB rows. Imported rows are always
is_verified=False and is_active=False. Existing Place rows are never updated.
Likely duplicates (matching name and nearby coords) are skipped.
The command may also create Category values for new candidates. This is an
explicit database update, not a migration. Back up your DB first.

REVIEW AT
    http://127.0.0.1:8000/admin/places/place/
Filter for unpublished/unverified records. Check operating status, legal
business names, address, CITY LOCATION, coordinates, and photo rights.
Use genuine licensed images with attribution. Assign relevant hobbies.
Only approve and publish after manual review. Avoid bulk-approving unknowns.
Until published, Phase 6A nearby search does NOT display these records.

ABOUT "AUTOMATIC" FETCHING
Each discovery command automatically asks Overpass for named OSM POIs.
You may schedule a LOW-FREQUENCY preview (e.g. weekly) using Windows Task
Scheduler, but scheduled fetching should never auto-publish OSM data.
Overpass does NOT certify that all businesses are complete or verified.
Google Places or other paid APIs can improve discovery but also require
credentials, usage controls, licensing review and separate integration.

SAFE ROLLBACK
Installation prints a backup manifest location and --restore command.
Restore deletes ONLY files introduced by this installer, and refuses to
remove them if changed later. No existing files were overwritten.

No Django models, migration files, auth permissions, MapTiler key, place
recommendation calculations, existing Place objects or Admin UI templates
are changed during installation. Your seven published places remain.
