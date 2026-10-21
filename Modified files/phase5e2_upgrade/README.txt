ExploreAnywhere Phase 5E.2 — Mobile Navigation & Image Decode

From your ExploreAnywhere project folder (with manage.py):

  .\venv\Scripts\Activate.ps1
  Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase5E2_Mobile_Images.zip" -DestinationPath ".\phase5e2_upgrade" -Force
  python ".\phase5e2_upgrade\exploreanywhere_phase5e2_mobile_images.py" --dry-run
  python ".\phase5e2_upgrade\exploreanywhere_phase5e2_mobile_images.py"
  python manage.py check
  python manage.py makemigrations --check --dry-run

The installer:
- Only updates: templates/theme/public_base.html, templates/places/saved_places.html,
  and templates/places/place_detail.html
- Refuses to overwrite unexpected source changes
- Preserves the existing map, search, ratings, photo sources, data, and workflows
- Makes an exact binary backup before writing changes; prints a rollback command
- Validates Django settings and template compilation, restoring upon failure
- Does NOT modify migrations, models, credentials, or database records

Mobile test: at <900px open the Menu, tap outside, open it again and press Escape,
check submenu More, tap a link, rotate the screen, and repeat on Android.
Image test: confirm genuine images load correctly on Saved Places and gallery;
hero photo remains prioritized. Chrome F12 > Network can be used to inspect actual loading.

This phase doesn't guarantee measurable speed improvement; compare timings in the
same browser and network. If dry run fails, stop and upload the latest source.
