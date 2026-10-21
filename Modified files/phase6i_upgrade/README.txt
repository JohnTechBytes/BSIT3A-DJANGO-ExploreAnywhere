EXPLOREANYWHERE — PHASE 6I: RETIRE HOBBY SELECTION
==================================================

PURPOSE
-------
Remove the redundant /hobbies/ selection screen as a required visitor step.
Visitors use Discover Kabankalan / Explore Places to search interests, select
a hobby filter, explore businesses and destinations, and use the map.

WHAT CHANGES
------------
- Hide the standalone "Hobbies" navigation item in homepage and public navbar.
- Direct old /hobbies/ and /hobbies/search/ routes to Explore Places.
  Existing search phrases (POST query or GET q) are forwarded as GET q.
- Redirect "Change Hobbies" links to the existing Explore Places hobby filter.
- Keep the existing hobby category data and 60/20 recommendation formula.
- Selecting a hobby in Explore Places supplies that hobby as the ranking input.
- Update any remaining old hobby links in user-facing templates (Journey, etc.).

NOT CHANGED
-----------
Database/migrations, published/unverified business records, saved places,
reviews, itineraries, visits, Admin permissions, maps, MapTiler provider/key.
The retired hobby-selection HTML template remains on disk unused; no records
or files are deleted.

INSTALLATION — RUN IN THE ROOT PROJECT DIRECTORY
------------------------------------------------
Activate your virtual environment:
    .\venv\Scripts\Activate.ps1

Extract the ZIP in Downloads to .\phase6i_upgrade:
    Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6I_Remove_Hobby_Selection.zip" -DestinationPath ".\phase6i_upgrade" -Force

Dry run:
    python ".\phase6i_upgrade\exploreanywhere_phase6i_remove_hobby_step.py" --dry-run

If dry run reports DRY RUN OK, install:
    python ".\phase6i_upgrade\exploreanywhere_phase6i_remove_hobby_step.py"

Installer runs Django checks and URL/template compilation, and restores all
changed files automatically on validation failure. It creates an exact
original-byte backup in phase6_backups/no-hobby-wizard-... .

TEST IN CHROME AFTER RESTARTING DJANGO
-------------------------------------
1. Navbar no longer displays a standalone "Hobbies" link.
2. http://127.0.0.1:8000/hobbies/ redirects to /places/?browse=all.
3. http://127.0.0.1:8000/hobbies/search/?q=waterfalls opens the search result.
4. http://127.0.0.1:8000/places/?browse=all displays all verified places.
5. Explore Places 'Explore by hobby' dropdown filters appropriately.
6. Search "coffee shop near me" opens nearby results.
7. Map styles, saved places, reviews, itineraries, Admin remain functional.
8. Check Android navigation and layout.

ROLLBACK
--------
Installer prints exact RESTORE command with the backup folder. Use it when
needed; restoration refuses to overwrite files edited after installation.

SECURITY
--------
The package contains only an installer and this README, not your project's
source code or MapTiler API key. No public Internet requests are made.
