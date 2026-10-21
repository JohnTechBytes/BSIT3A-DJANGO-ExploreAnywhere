EXPLOREANYWHERE — PHASE 6E: SMART NEARBY SEARCH
===============================================

WHAT THIS VERSION DOES
- Fixes exact business-name searches: "Coffee & Talk" now returns that verified listing
  instead of every coffee shop.
- Adds type-ahead suggestions backed ONLY by verified + active Kabankalan records.
  Selecting one opens its Nearby result and existing Place Details link.
- Adds one-tap searches for Coffee, Restaurants, Barbers, Malls and Billiards.
- Shows actual visitor review rating only where existing reviews exist.
- Adds staff-verified badges, clearer business contact notes, photo credits and
  visible OpenStreetMap attribution.
- Preserves user-triggered browser-only GPS sorting or landmark sorting,
  straight-line distances and Google Maps directions.
- Fixes the "250 result limit" warning so it appears only when results exceed 250.

SAFETY
Only two files changed:
  apps/places/nearby.py
  templates/places/nearby_places.html
No models, migrations, database records, API keys, Admin review queue, or permissions
are modified. Imported OSM candidates remain hidden until independently verified
AND published. Do not publish unverified businesses just to test the interface.

SOURCE VERSION
Based on the user's current Phase 6D source snapshot (Nearby files unchanged
by Phase 6D.1). Installer refuses unknown edits rather than overwriting work.

INSTALLATION (VS CODE / POWERSHELL, in project root)
1. .\venv\Scripts\Activate.ps1
2. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6E_Nearby_Recommendations.zip" -DestinationPath ".\phase6e_upgrade" -Force
3. python ".\phase6e_upgrade\exploreanywhere_phase6e_nearby_upgrade.py" --dry-run
4. python ".\phase6e_upgrade\exploreanywhere_phase6e_nearby_upgrade.py"
5. python manage.py check
6. python manage.py makemigrations --check --dry-run

Browser: http://127.0.0.1:8000/places/nearby/
Test: coffee shop near me, Coffee & Talk, business categories, empty states.
Typing part of a published business name shows matching verified places. Since
all 175 OSM candidates are unverified, they do NOT appear in public searches.
Verify with a genuinely approved business only when available.

GPS ON ANDROID
The http://HOTSPOT_IP:8000 local website normally does not have the secure context
required for Geolocation. Use a verified Kabankalan landmark selector for
local demos; later deploy behind HTTPS for consent-based GPS. Never disable
browser security just to make GPS work.

ROLLBACK
Installation prints the exact --restore command pointing to a folder under
phase6_backups. Rollback refuses to clobber source edits made after installation.

ACTUAL VALIDATION
This ZIP has offline installer, Windows-CRLF, JS-syntax and restoration tests.
The Django check and template rendering occur in the user's venv during install.
