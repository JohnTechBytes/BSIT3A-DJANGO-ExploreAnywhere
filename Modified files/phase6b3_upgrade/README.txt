ExploreAnywhere Phase 6B.3 — Nominatim Boundary & Smaller OSM Business Queries
========================================================================

Requires installed Phase 6B.2 command and project-root working directory.
Only apps/places/management/commands/discover_kabankalan_businesses.py is changed.
It never changes models, migrations, existing records, publication flags or user permissions.

1. Extract the ZIP, keep payload/ next to the installer.
2. Activate your virtual environment. Run from ExploreAnywhere folder with manage.py.
3. python .\phase6b3_upgrade\exploreanywhere_phase6b3_importer_repair.py --dry-run
4. python .\phase6b3_upgrade\exploreanywhere_phase6b3_importer_repair.py
5. python manage.py check
6. python manage.py discover_kabankalan_businesses --boundary-only
7. ONLY IF Step 6 succeeds, test one small subset:
   python manage.py discover_kabankalan_businesses --category coffee

It queries Nominatim ONCE per command for an OSM administrative relation and validates
Kabankalan + Negros Occidental + Philippines. If Nominatim has no unambiguous match,
STOP: do not invent a relation ID or city bounding box.
The category test fetches ONLY coffee shops and writes a JSON snapshot, NOT a DB import.

A full snapshot may require multiple category queries and several seconds' gaps.
Any failed category aborts the fetch without writing a partial full snapshot.
Do NOT retry overloaded public mapping services repeatedly. Observe Nominatim's
max 1 request per second and OSM attribution requirements. The command uses one
Nominatim lookup per run, not bulk POI searches through Nominatim.

When a preview file is reviewed, --import-snapshot --dry-run displays proposed
new records. ONLY a separate explicit import creates inactive, unverified rows.
New business listings must be verified by a staff member before publishing.
OSM does not guarantee current opening hours or complete coverage.

Restoration command is printed after installation.
