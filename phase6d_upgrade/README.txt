EXPLOREANYWHERE — PHASE 6D: BUSINESS VERIFICATION QUEUE
========================================================

PURPOSE
-------
Your Phase 6C dry run found 175 new OSM candidates but did NOT stage them.
Phase 6D adds a permission-controlled queue at:
    http://127.0.0.1:8000/admin/places/place/osm-review/

The queue lists staged OSM businesses separately from the ordinary Kabankalan
Destination Manager. It links to OSM sources, shows review status, and requires
an independent verification checkbox, source/date note, and location confirmation
before an imported business can be marked verified or active. Its bulk approve
action skips imported OSM records. It uses existing Django Admin History;
there are no new models or migrations.

INSTALL — RUN IN VS CODE POWERSHELL AT THE DIRECTORY CONTAINING manage.py
------------------------------------------------------------------------
1. .\venv\Scripts\Activate.ps1
2. Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6D_Business_Review_Queue.zip" -DestinationPath ".\phase6d_upgrade" -Force
3. python ".\phase6d_upgrade\exploreanywhere_phase6d_review_queue.py" --dry-run
4. If and only if DRY RUN OK:
   python ".\phase6d_upgrade\exploreanywhere_phase6d_review_queue.py"
5. python manage.py check
6. python manage.py makemigrations --check --dry-run
7. Stop Django with Ctrl+C and restart: python manage.py runserver
8. Open /admin/places/place/osm-review/ in your browser.

BEFORE IMPORTING ANY CANDIDATES
-------------------------------
The new queue is initially empty because your previous step was only a dry run.
Confirm first:
  • The Admin queue loads and the sidebar shows Business review.
  • The Destinations page still contains your existing published destinations.
  • Your Admin user's permitted controls remain usable.
  • A view-only or unauthorized staff member cannot approve anything.

OPTIONAL STAGING (DATABASE WRITE — ONLY AFTER TESTING & BACKUP)
--------------------------------------------------------------
The snapshot was created on your computer and is NOT inside this ZIP:
  phase6_imports\kabankalan_osm_offline_20261017_141641.json

1. Back up your MySQL database first, using your trusted database backup method.
2. Confirm preview is still correct:
   python manage.py discover_kabankalan_businesses --import-snapshot ".\phase6_imports\kabankalan_osm_offline_20261017_141641.json" --dry-run
3. ONLY after deciding to stage the unverified records, run:
   python manage.py discover_kabankalan_businesses --import-snapshot ".\phase6_imports\kabankalan_osm_offline_20261017_141641.json"
4. Check pending candidates in the review queue.

The import command from Phase 6B creates new Place records INACTIVE and
UNVERIFIED (and may create new Category records). It is separate from this
installer; Phase 6D itself makes NO database writes and DOES NOT stage imports.

REVIEW EACH BUSINESS
--------------------
In Admin, select Business review > a candidate > Review/edit.
Inspect its OSM source, but do NOT treat OSM alone as business verification.
Independently check name, actual operating status, category and real location;
update contact details if reliable. Include evidence source and date in the
review notes and confirm location when switching a candidate to verified or
active. Django Admin History retains the evidence note from the status change.
Only records with BOTH is_verified=True and is_active=True appear publicly.
A reviewer may first verify with is_active=False and publish later.

SAFETY / LIMITATIONS
--------------------
• Imported OSM candidates are identified from source slugs osm-<type>-<id>.
• Pending, unverified OSM records are hidden in the ordinary destination table,
  but remain accessible through the Admin review queue and authorized edit page.
• The bulk publication action cannot approve OSM records.
• The queue's source links provide provenance, not proof of current operation.
• OSM mapped coverage is incomplete; your snapshot found 0 billiards entries.
• No automatic publishing; no changes to recommendation formula, maps, visit
  approval, user permissions, migration files or database schema.
• Source attribution: © OpenStreetMap contributors (ODbL).
• Distinct REJECTED status and immutable verification evidence would need a
  future model/migration; Phase 6D uses existing flags and Django Admin History.

ROLLBACK
--------
The installer prints an exact command with the backup path. Example:
  python ".\phase6d_upgrade\exploreanywhere_phase6d_review_queue.py" --restore "phase6_backups\business-review-YYYYMMDD-HHMMSS-ffffff"
The restoration refuses to overwrite manual code changes made after installation.
Rolling back source code does NOT undo any OPTIONAL database imports.

If validation fails during installation, installer automatically restores
original files. Source tests are not equivalent to browser/security tests.
