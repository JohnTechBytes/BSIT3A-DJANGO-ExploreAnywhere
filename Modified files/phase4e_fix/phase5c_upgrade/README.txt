# ExploreAnywhere Phase 5C.1 — Personal Journey UI

Template-only enhancement based on `ExploreAnywhere_Phase5C_Source.zip`.

## What changed

- **My Kabankalan Journey:** "Explore Places" and browse-empty-state links open `?browse=all` directly, while "Find recommendations" retains its hobby-selection function. Adds a clear *next badge* progress indicator based on existing `approved_visit_count`; approved visits only, thresholds 1 / 3 / 5. Does not grant badges or points.
- **Saved Places:** Browse All link resets prior search; a first-save empty-state call-to-action.
- **My Itineraries:** Optional instant search *of already displayed, user-owned trip cards*. Nothing is sent to the server or written to the database.
- **My Visits:** Optional All / Pending / Approved / Rejected display filters, status explanation, and accessible match count. Status does not change; staff approvals remain entirely in your existing workflow.

## Install on Windows PowerShell (from project folder)

1. ` .\venv\Scripts\Activate.ps1 `
2. ` Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase5C_Journey_Upgrade.zip" -DestinationPath ".\phase5c_upgrade" -Force `
3. ` python ".\phase5c_upgrade\exploreanywhere_phase5c_journey_upgrade.py" --dry-run `
4. When it reports DRY RUN OK: ` python ".\phase5c_upgrade\exploreanywhere_phase5c_journey_upgrade.py" `
5. ` python manage.py check `
6. ` python manage.py makemigrations --check --dry-run `
7. Start Django and test `/places/journey/`, `/places/saved/`, `/itineraries/` and `/visits/` on desktop + Android.

## Safeguards

- Changes **only four HTML templates**. No Python views, URLs, recommendations, models, migrations, user data, map keys, rewards code or database.
- Checks uploaded-source fingerprints before installation; stops without changes if files have changed.
- Creates `phase5_backups/journey-ui-<timestamp>` with the originals and a rollback manifest.
- Installer prints your exact `--restore` command. Restore refuses if a file has been edited after the upgrade.
- JavaScript is optional: trip/visit listings remain readable if JavaScript is disabled.
- Phase 5C.1 does **not** change trip stops or visit approval records.

## Test cases

1. Journey hero **Explore Places** goes to `/places/?browse=all`, **Find recommendations** goes to Hobbies.
2. Journey next badge shows `First Explorer` before the first approved visit; progress uses only approved count.
3. Visit badges and points remain identical to before.
4. My Itineraries search narrows cards by trip name, clearing the search restores the cards; opening a trip still works.
5. My Visits status filters show only matching entries; **All** restores them; actions still work.
6. Saved Places can browse all Kabankalan destinations and save/remove records as before.
7. Security: check authenticated ownership, read-only display filters, and staff-only visit verification.
8. Android: no horizontal overflow, filters are tappable, focus indicators visible.

If `--dry-run` fails, stop and send its message. Do not force the upgrade over edited files.
