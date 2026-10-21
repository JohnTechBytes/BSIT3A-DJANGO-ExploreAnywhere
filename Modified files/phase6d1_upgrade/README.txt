EXPLOREANYWHERE — PHASE 6D.1 BUSINESS VERIFICATION FORM CLEANUP
==============================================================

Only files changed:
  apps/places/admin.py
  templates/admin/places/place/change_form.html [new]

This is an interface-only arrangement for OSM-imported businesses.
Original Kabankalan destinations retain their existing fieldsets.
No migrations, SQL updates or changes to forms.py or publication actions.
All imported business verification requirements remain in forms.py.

1. Extract the ZIP into <project>/phase6d1_upgrade.
2. From the project root, with venv active:
   python ".\phase6d1_upgrade\exploreanywhere_phase6d1_business_form.py" --dry-run
3. Proceed only if DRY RUN OK:
   python ".\phase6d1_upgrade\exploreanywhere_phase6d1_business_form.py"
4. Run:
   python manage.py check
   python manage.py makemigrations --check --dry-run
5. Restart Django and open an OSM business from Business Review.

FORM CHANGES
- Simplified top section for identity, business category and location.
- Publication controls grouped next to independent evidence and source.
- Public description and hobbies separate from optional data.
- Contact, photo rights and administrative metadata collapsed by default.
- Mobile sizing for hobby selector and input fields.
- 'Save and add another' hidden only on imported edit forms (other save
  actions remain available).
- A Back to Business Review link for imported business forms.
- Opening hours and gallery inlines remain accessible and unchanged.

SECURITY TEST (only when ready)
Open an unverified imported business, and try to check Is Active and
Is Verified WITHOUT checking independent evidence or entering review notes.
The form should display errors and refuse to publish. Do not fabricate
an evidence note or approve a real business just to test the interface.

DO NOT publish the 175 imported OSM entries in bulk. Each entry requires
independent confirmation, including its actual operation and location.

Installer prints a --restore command and stores originals in phase6_backups.
If local source files don't match the previously installed Phase 6D package,
the installer will stop without modifying them; upload the current files instead.
