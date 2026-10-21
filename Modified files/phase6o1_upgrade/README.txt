ExploreAnywhere Phase 6O.1 — Network Diagnostics and Targeted Retries

This upgrade replaces ONLY apps/places/management/commands/phase6o_business_photos.py.
It changes NO records or migrations. The command still requires individual reviewer decisions before photo metadata can be applied.

1) From ExploreAnywhere project root, activate your venv.
2) Expand ZIP to .\phase6o1_upgrade.
3) python ".\phase6o1_upgrade\exploreanywhere_phase6o1_network_fix.py" --dry-run
4) python ".\phase6o1_upgrade\exploreanywhere_phase6o1_network_fix.py"
5) python manage.py check

Your previous EXPLOREANYWHERE_PHOTO_USER_AGENT session variable must still be set, with a genuine project contact.

Diagnostic (READ ONLY, 3 public API requests):
    python manage.py phase6o_business_photos --diagnose-network

Retry only the three original lookup errors; don't repeat previously negative cases:
    python manage.py phase6o_business_photos --collect --retry-errors --limit 10

Expected: More informative errors (including repr(exc.reason)) and bounded retries for transient errors (max 2 attempts).
If APIs are consistently blocked or slow, do not keep running retries. Consider owner-provided and appropriately licensed photos instead.

The collector writes ONLY the existing phase6_photo_review CSV and gallery. It never changes business verification / publication.
No auto-approval. No promise that the seven with no direct Commons links have photos.

Installer creates a ZIP backup in phase6_backups and prints a --restore command.
If current command differs from the previously supplied file, installer refuses to modify it.
