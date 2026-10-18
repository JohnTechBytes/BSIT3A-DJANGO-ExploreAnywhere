ExploreAnywhere Phase 6M — Clean Discover Navigation
====================================================
Purpose
- Remove duplicate 'Popular searches' bar from Discover mode navigation.
- Remove the long explanation under the All Places / Near Me / Map View tabs.
- Remove the redundant '← All Places' link from Near Me header.
- Keep the three working tabs and the single Near Me quick-search bar.
- Preserve existing MapTiler, landmark, GPS, distance, and search logic.

Requirements
- Phase 6L has been installed successfully.
- Run PowerShell from the project folder containing manage.py.
- Use the project virtual environment.

PowerShell:
.\venv\Scripts\Activate.ps1
Expand-Archive -LiteralPath "$env:USERPROFILE\Downloads\ExploreAnywhere_Phase6M_Clean_Discovery.zip" -DestinationPath ".\phase6m_upgrade" -Force
python ".\phase6m_upgrade\exploreanywhere_phase6m_remove_duplicates.py" --dry-run
python ".\phase6m_upgrade\exploreanywhere_phase6m_remove_duplicates.py"
python manage.py check

The installer backs up two original template files into phase6_backups and
checks Django plus template compilation. It automatically rolls back on a
validation failure. No migrations, business records, or admin logic change.

To restore manually, copy the --restore command printed by the installer.

Test in browser:
- /places/?mode=nearby: the tabs remain, no duplicate Popular searches,
  no long explanation, no header '← All Places', quick search still works.
- /places/?browse=all: All Places navigation and filters still work.
- /places/?browse=all&display=map: Map View still works.
- GPS, optional Kabankalan landmark, radius, map pins, and business cards.
- Test on Android too.

If --dry-run fails, do not override source checks; share the error and your
current templates to generate an updated patch.
