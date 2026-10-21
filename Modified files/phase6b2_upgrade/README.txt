ExploreAnywhere — Phase 6B.2 Overpass Query Optimization

WHY:
Your small Overpass query returned HTTP 200, but the original global Kabankalan
boundary lookup returned HTTP 500. This update makes that first query use exact
name indexes, adds --boundary-only to test it separately, and labels errors by
query stage. Exact-name lookup may still fail if the public service is busy.

INSTALL FROM THE ExploreAnywhere PROJECT DIRECTORY:
  python ".\phase6b2_upgrade\exploreanywhere_phase6b2_query_fix.py" --dry-run
  python ".\phase6b2_upgrade\exploreanywhere_phase6b2_query_fix.py"
  python manage.py check

FIRST NETWORK TEST (ONE lightweight query; NO database write):
  python manage.py discover_kabankalan_businesses --boundary-only

IF THE BOUNDARY TEST SUCCEEDS, LATER FETCH THE FULL PREVIEW (NO DB write):
  python manage.py discover_kabankalan_businesses

If the full preview fails due to HTTP 500, do not keep retrying. Copy the
stage-specific error back to ChatGPT; we can split the business discovery
query into smaller categories.

SAFETY:
- This installer only edits apps/places/management/commands/discover_kabankalan_businesses.py
- Installation does not call any network endpoints or write to the database.
- Both fetch commands are read-only and only save JSON on successful full fetch.
- --import-snapshot is unchanged, creates inactive/unverified candidates only,
  and must be explicitly requested after reviewing a JSON snapshot.
- Existing verified places and Django Admin settings are untouched.
- The optional --relation-id still requires an ACTUAL, checked OSM relation ID;
  do not invent one or substitute a guessed-radius query.
- The existing Overpass.kumi.systems endpoint remains the default.
- Follow Overpass fair-use practices and OpenStreetMap attribution rules.

TO RESTORE:
  Use the exact --restore command printed by the installer.
