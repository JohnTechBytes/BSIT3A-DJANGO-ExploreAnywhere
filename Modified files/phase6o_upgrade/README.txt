ExploreAnywhere Phase 6O — Kabankalan business photo candidates
==============================================================
Read-only collector + manually approved Wikimedia Commons cover-photo importer.
This does NOT verify or publish businesses and does NOT download or upload photos.
Not all businesses have a real photo on Commons. Never substitute unrelated photos.

INSTALL (from your ExploreAnywhere project root):
1. Expand the ZIP into phase6o_upgrade.
2. python phase6o_upgrade/exploreanywhere_phase6o_install.py --dry-run
3. python phase6o_upgrade/exploreanywhere_phase6o_install.py
4. python manage.py phase6o_business_photos --inventory

COLLECT PHOTOS (requires internet and correct contact in User-Agent):
In PowerShell set (replace with your REAL contact email):
 $env:EXPLOREANYWHERE_PHOTO_USER_AGENT='ExploreAnywhere-School-Project/1.0 (contact: you@yourdomain.com)'
Then run a small pilot:
 python manage.py phase6o_business_photos --collect --limit 10
Or collect all missing-cover OSM places (may take several minutes):
 python manage.py phase6o_business_photos --collect --all

REVIEW:
Open phase6_photo_review/kabankalan_photo_gallery.html in your browser.
Open phase6_photo_review/kabankalan_photo_review.csv in Excel or a text editor.
For EACH correctly matched and appropriately licensed candidate you inspect:
 - review_decision: approve
 - identity_checked: yes
 - rights_checked: yes
 - review_notes: cite your independent evidence it shows that exact place and
   why it may legally be used, e.g. observed original Commons page and business logo
Keep other rows blank or mark reject. A Wikimedia/OSM tag is only a candidate, NOT
independent proof of the business's identity, activity, or image rights.
Save CSV preserving the header, UTF-8 and comma delimiter.

PREVIEW APPROVALS (no DB writes):
 python manage.py phase6o_business_photos --apply-approved --dry-run

APPLY *ONLY REVIEWED* COVER URLS (DB PHOTO FIELDS CHANGED):
Back up exploreanywhere MySQL database FIRST, then run:
 python manage.py phase6o_business_photos --apply-approved --confirm-reviewed

Covers on existing places are never overwritten. Not a business verification tool.
The command never changes city, name, verification, active status or category.
Only HTTPS Wikimedia image URLs with a supported Creative Commons license,
creator credit, source, and license URL can be applied. CC BY/CC BY-SA licenses
require attribution (and applicable share-alike obligations).

If Commons or OSM block requests, or no linked candidate is available, leave
those businesses without a photo until the owner grants permission / supplies
an authentic, properly licensed photograph. No generic stock photos are assigned.

COLLECTED FILES:
 phase6_photo_review/kabankalan_photo_review.csv
 phase6_photo_review/kabankalan_photo_gallery.html

SAFETY:
- Source installer adds only apps/places/management/commands/phase6o_business_photos.py
- Django validation with automatic source rollback
- No migrations, edits of other app files, or implicit database writes
- Committed approval changes need a normal database SQL backup for reversal
- Source command can be removed with installer's --restore <backup_zip>
