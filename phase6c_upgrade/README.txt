ExploreAnywhere Phase 6C — OFFLINE OSM BUSINESS EXTRACT

Why: Your working Nominatim Kabankalan boundary lookup identified OSM relation 3740502, but public Overpass interpreter queries returned HTTP 500 even for a small node probe. Do not repeatedly retry it.

1. Download a Kabankalan area OSM extract (.osm.pbf or .osm) using a legitimate OpenStreetMap extract provider such as https://extract.bbbike.org/ (custom area). Select Kabankalan City, Negros Occidental, and extend the selection to cover the full city boundary. If the custom extract cannot cover the whole city, its results will be incomplete. Review any provider download terms. The Philippines Geofabrik extract at https://download.geofabrik.de/asia/philippines.html is another option but is much larger and uses more mobile data.
2. Keep the downloaded file outside the Git repository (e.g. in Downloads). Never upload a huge extract to GitHub.
3. Install this command: python exploreanywhere_phase6c_offline_importer.py --dry-run, then python exploreanywhere_phase6c_offline_importer.py
4. If the file is .osm.pbf (recommended), once inside the virtual environment: python -m pip install osmium
5. In the project root, run: python manage.py import_kabankalan_osm_extract "$env:USERPROFILE\Downloads\YOUR_FILENAME.osm.pbf" --category coffee
   OR if it is .osm XML: python manage.py import_kabankalan_osm_extract "$env:USERPROFILE\Downloads\YOUR_FILENAME.osm" --category coffee
   This creates a preview file under phase6_imports/, without importing or publishing database records.
6. Preview the JSON file. DRY RUN the existing staging importer:
   $snapshot = Get-ChildItem .\phase6_imports\kabankalan_osm_offline_*.json | Sort-Object LastWriteTime -Descending | Select-Object -First 1 -ExpandProperty FullName
   python manage.py discover_kabankalan_businesses --import-snapshot "$snapshot" --dry-run
7. Only if the snapshot and duplicate report are correct, explicitly stage new records as INACTIVE and UNVERIFIED:
   python manage.py discover_kabankalan_businesses --import-snapshot "$snapshot"
8. Verify each business in Django Admin before activating it. Not all businesses in OSM are current or complete. You must verify each listing's identity, actual location, operation and any image rights. Keep your seven verified destinations unchanged.

The command uses the Nominatim verified administrative relation polygon to test coordinates; one initial Nominatim polygon lookup may be needed, then it uses the cached polygon. There are NO Overpass requests.

Requirements and limitations:
- Supports named OSM nodes and ways. OSM multipolygon relations are not imported by this initial extractor, so some mapped buildings may be omitted.
- For way polygons, the average node position is used as an approximate marker, and it may be outside a concave or irregular polygon. Administrator must verify it.
- OSM extracts are incomplete and not a verified business registry. Missing names and positions are discarded. A supplied extract covering only part of the city produces only partial results.
- The source must be attributed as © OpenStreetMap contributors (ODbL): https://www.openstreetmap.org/copyright and reviewed for any ODbL obligations when redistributing a derivative database.
- The Nominatim cache under phase6_imports is an auxiliary file and can be reviewed; installer only modifies one new management command, no models or database tables.
- For Android GPS over HTTP on a LAN IP, browsers may restrict geolocation. Distance fallback via verified landmarks remains supported.
