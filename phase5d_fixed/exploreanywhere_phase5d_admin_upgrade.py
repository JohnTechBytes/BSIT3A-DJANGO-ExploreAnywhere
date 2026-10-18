#!/usr/bin/env python3
"""ExploreAnywhere Phase 5D.1 — reversible Django Admin visual redesign.

Run from the Django project root. This does not update existing admin classes,
permissions, review actions, models, records, migrations, or settings.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from datetime import datetime

ROOT = Path.cwd().resolve()
PACKAGE = Path(__file__).resolve().parent
PAYLOAD = PACKAGE / "payload"
FILES = (
    "templates/admin/base_site.html",
    "templates/admin/index.html",
    "apps/places/templatetags/ea_admin_summary.py",
    "apps/places/templatetags/__init__.py",
)
SIGNATURE = "ExploreAnywhere Phase 5D.1"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def die(message: str) -> None:
    raise RuntimeError(message)


def check_project() -> None:
    required = ("manage.py", "mysite/urls.py", "apps/places/admin.py", "apps/visits/admin.py")
    missing = [item for item in required if not (ROOT / item).is_file()]
    if missing:
        die("This is not the expected ExploreAnywhere project root. Missing: " + ", ".join(missing))
    place_admin = (ROOT / "apps/places/admin.py").read_text(encoding="utf-8-sig")
    visits_admin = (ROOT / "apps/visits/admin.py").read_text(encoding="utf-8-sig")
    if "KABANKALAN_CITY_ID = 2" not in place_admin or "KabankalanPlaceAdminForm" not in place_admin:
        die("Destination Manager differs from the reviewed source; refusing to install.")
    if "approve_reviewed" not in visits_admin or "reviewer_note" not in visits_admin:
        die("Visit approval safeguards differ from the reviewed source; refusing to install.")
    for name in FILES:
        if not (PAYLOAD / name).is_file():
            die("Installer payload incomplete: " + name)


def check_targets() -> tuple[list[tuple[str, bytes, bytes | None]], bool]:
    changes = []
    unchanged = 0
    for name in FILES:
        target = ROOT / name
        if target.is_symlink():
            die("Refusing to modify symlink: " + name)
        new = (PAYLOAD / name).read_bytes()
        old = target.read_bytes() if target.exists() else None
        if old == new:
            unchanged += 1
        elif old is not None and name == "apps/places/templatetags/__init__.py":
            # Never overwrite an existing package initializer.
            print("PRESERVED: Existing apps/places/templatetags/__init__.py")
            unchanged += 1
        elif old is not None:
            die("Existing custom file differs from this package: " + name +
                ". No changes made. Please upload the file for a merge-safe update.")
        else:
            changes.append((name, new, old))
    return changes, unchanged == len(FILES)


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=str(path.parent), prefix=".ea_admin_", delete=False) as f:
        temp = Path(f.name)
        f.write(data)
    try:
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def verify_django_template_resolution() -> None:
    # Executing a script under ./phase5d_upgrade puts that subfolder on sys.path,
    # not necessarily the Django project root. Match manage.py import resolution.
    project_root = str(ROOT)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mysite.settings")
    import django
    django.setup()
    from django.template.loader import get_template
    for name in ("admin/base_site.html", "admin/index.html"):
        resolved = Path(get_template(name).origin.name).resolve()
        expected = (ROOT / "templates" / name).resolve()
        if resolved != expected:
            die(f"Django did not load the custom {name} (resolved: {resolved}). "
                "Your project may need BASE_DIR / 'templates' in TEMPLATES[0]['DIRS'].")
    print("PASS: Django resolves the redesigned admin templates.")


def restore(backup_arg: str, *, force_after_failure=False) -> None:
    backup = Path(backup_arg)
    if not backup.is_absolute():
        backup = ROOT / backup
    backup = backup.resolve()
    manifest_file = backup / "manifest.json"
    if not manifest_file.is_file():
        die("Backup manifest not found: " + str(manifest_file))
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    entries = manifest.get("files", [])
    if {entry["path"] for entry in entries} != {name for name in FILES}:
        die("Backup manifest contains an unexpected file set; refusing restore.")
    for entry in entries:
        name = entry["path"]
        target = ROOT / name
        if target.is_symlink():
            die("Unsafe symlink during restore: " + name)
        current = target.read_bytes() if target.exists() else None
        if not force_after_failure and current is not None and digest(current) != entry["installed_hash"]:
            die("File was edited after installation, so automatic restore stopped: " + name)
        if entry["existed"] and not (backup / name).is_file():
            die("Original backup file is missing: " + name)
    for entry in entries:
        name = entry["path"]
        target = ROOT / name
        if entry["existed"]:
            atomic_write(target, (backup / name).read_bytes())
        elif target.exists():
            target.unlink()
    print("RESTORED: Original admin files and template state from", backup)
    print("Models, visit records, credentials and database were never changed.")


def install() -> None:
    check_project()
    changes, all_same = check_targets()
    if all_same:
        print("ALREADY INSTALLED: Phase 5D.1 admin visuals match this package.")
        verify_django_template_resolution()
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    backup = ROOT / "phase5_backups" / ("admin-sidebar-" + stamp)
    backup.mkdir(parents=True, exist_ok=False)
    manifest = {"version": "5D.1", "files": []}
    for name in FILES:
        target = ROOT / name
        original = target.read_bytes() if target.exists() else None
        # Existing __init__.py is deliberately not touched.
        changed = any(x[0] == name for x in changes)
        installed = (PAYLOAD / name).read_bytes() if changed else (original or b"")
        manifest["files"].append({
            "path": name,
            "existed": original is not None,
            "installed_hash": digest(installed),
        })
        if original is not None:
            backup_file = backup / name
            backup_file.parent.mkdir(parents=True, exist_ok=True)
            backup_file.write_bytes(original)
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    try:
        for name, new, _old in changes:
            atomic_write(ROOT / name, new)
        verify_django_template_resolution()
    except Exception:
        print("INSTALL VALIDATION FAILED: restoring the original state immediately.", file=sys.stderr)
        restore(str(backup), force_after_failure=True)
        raise
    print("SUCCESS: ExploreAnywhere Phase 5D.1 admin sidebar and dashboard installed.")
    print("Created new admin templates and a permission-aware read-only metric tag.")
    print("No existing admin registrations, business logic, settings, database or migrations changed.")
    print("Backup:", backup.relative_to(ROOT))
    print('Restore: python "' + str(Path(__file__).resolve()) + '" --restore "' + str(backup.relative_to(ROOT)) + '"')
    print("Next: python manage.py check; then open /admin/ and test desktop and Android.")


def main() -> None:
    parser = argparse.ArgumentParser(description=SIGNATURE)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--dry-run", action="store_true")
    modes.add_argument("--restore", metavar="BACKUP_DIRECTORY")
    args = parser.parse_args()
    try:
        if args.restore:
            restore(args.restore)
            return
        check_project()
        changes, all_same = check_targets()
        if args.dry_run:
            if all_same:
                print("DRY RUN OK: Theme is already installed.")
            else:
                print("DRY RUN OK: New permission-aware Django Admin templates can be added safely.")
            print("Targets:", ", ".join(FILES))
            print("Preserved: destination verification, staff approval actions, admin permissions, DB, migrations.")
            return
        install()
    except Exception as exc:
        print("ERROR:", exc, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
