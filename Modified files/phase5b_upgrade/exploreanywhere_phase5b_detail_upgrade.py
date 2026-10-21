#!/usr/bin/env python3
"""ExploreAnywhere Phase 5B — safe destination-detail UI installer.

Only touches apps/places/views.py and templates/places/place_detail.html.
Never changes databases, migrations, models, credentials, or image files.

Usage:
  python exploreanywhere_phase5b_detail_upgrade.py --dry-run
  python exploreanywhere_phase5b_detail_upgrade.py
  python exploreanywhere_phase5b_detail_upgrade.py --restore phase5_backups/detail-ui-...
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import sys
from datetime import datetime

VIEW_REL = Path("apps/places/views.py")
DETAIL_REL = Path("templates/places/place_detail.html")
SOURCE_HASHES = {
    str(VIEW_REL): "6d235bc2e1433d8bfcef0d82e46991d5bfc24379d24886c5e76b1f7823b9f326",
    str(DETAIL_REL): "cff163d04bb788e1cb7c08a9129ff7a65ac62124493293196b288b9be4ee5680",
}
DETAIL_ASSET = "place_detail_phase5b.html"
VIEW_OLD = '"photos", "opening_hours"'
VIEW_NEW = '"photos", "opening_hours", "hobbies"'
MARKER = "ExploreAnywhere Phase 5B: destination-detail presentation only."


def sha(content):
    return hashlib.sha256(content).hexdigest()


def atomic_write(path, content):
    tmp = path.with_name(f".{path.name}.phase5b-{secrets.token_hex(5)}.tmp")
    try:
        with tmp.open("wb") as fh:
            fh.write(content)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


def find_project():
    folder = Path.cwd().resolve()
    if not (folder / "manage.py").is_file():
        raise RuntimeError("Run this script in your ExploreAnywhere project folder (where manage.py exists).")
    if not (folder / VIEW_REL).is_file() or not (folder / DETAIL_REL).is_file():
        raise RuntimeError("Missing apps/places/views.py or templates/places/place_detail.html.")
    return folder


def plan(root):
    originals = {str(p): (root / p).read_bytes() for p in (VIEW_REL, DETAIL_REL)}
    old_view = originals[str(VIEW_REL)]
    old_detail = originals[str(DETAIL_REL)]
    if MARKER.encode() in old_detail:
        if VIEW_NEW.encode() in old_view:
            return originals, None
        raise RuntimeError("Detail template appears upgraded but the view prefetch is missing; cannot install safely.")

    # Check compatibility BEFORE any file/backup changes; never guess around changes.
    for rel, data in originals.items():
        normalized = data.replace(b"\r\n", b"\n")
        if sha(normalized) != SOURCE_HASHES[rel]:
            raise RuntimeError(f"Source differs from the uploaded Phase 5B snapshot: {rel}. "
                               "Upload your latest file; nothing was changed.")
    view_text = old_view.decode("utf-8-sig")
    if view_text.count(VIEW_OLD) != 1:
        raise RuntimeError("Expected one Place Details prefetch declaration; refusing to patch.")
    new_view = view_text.replace(VIEW_OLD, VIEW_NEW, 1)
    if old_view.startswith(b"\xef\xbb\xbf"):
        new_view = "\ufeff" + new_view
    asset = Path(__file__).resolve().with_name(DETAIL_ASSET)
    if not asset.is_file():
        raise RuntimeError(f"Missing {DETAIL_ASSET}; extract the full ZIP, then rerun.")
    new_detail = asset.read_bytes()
    if MARKER.encode() not in new_detail:
        raise RuntimeError("The bundled HTML asset does not contain the expected version marker.")
    if old_detail.count(b"\r\n"):
        new_detail = new_detail.replace(b"\n", b"\r\n")
    changed = {str(VIEW_REL): new_view.encode("utf-8"), str(DETAIL_REL): new_detail}
    return originals, changed


def restore(root, backup_arg):
    directory = Path(backup_arg)
    if not directory.is_absolute():
        directory = root / directory
    directory = directory.resolve()
    allowed = (root / "phase5_backups").resolve()
    if allowed != directory and allowed not in directory.parents:
        raise RuntimeError("Restore path must be inside this project's phase5_backups folder.")
    manifest_path = directory / "manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError(f"No Phase 5B backup manifest at: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("kind") != "exploreanywhere-phase5b-detail":
        raise RuntimeError("This backup was not created by the Phase 5B installer.")
    for rel in (str(VIEW_REL), str(DETAIL_REL)):
        target = root / rel
        previous = (directory / Path(rel).name).read_bytes()
        if sha(previous) != manifest["previous"][rel]:
            raise RuntimeError(f"Corrupt backup: {rel}. No files restored.")
        if sha(target.read_bytes()) != manifest["installed"][rel]:
            raise RuntimeError(f"Current {rel} changed after upgrade. Refusing to overwrite later edits.")
    for rel in (str(VIEW_REL), str(DETAIL_REL)):
        atomic_write(root / rel, (directory / Path(rel).name).read_bytes())
    print("RESTORED: Original Phase 5B source files are back in place.")
    print("Database, migrations, photos and other project files remain unchanged.")


def install(root, originals, changes):
    backup = (root / "phase5_backups" /
              ("detail-ui-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f") + "-" + secrets.token_hex(3)))
    backup.mkdir(parents=True)
    for rel, contents in originals.items():
        shutil.copyfile(root / rel, backup / Path(rel).name)
        if (backup / Path(rel).name).read_bytes() != contents:
            raise RuntimeError(f"Backup readback failed: {rel}. No project files changed.")
    manifest = {
        "kind": "exploreanywhere-phase5b-detail",
        "previous": {rel: sha(data) for rel, data in originals.items()},
        "installed": {rel: sha(data) for rel, data in changes.items()},
    }
    (backup / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    try:
        for rel, data in changes.items():
            atomic_write(root / rel, data)
        for rel, data in changes.items():
            if (root / rel).read_bytes() != data:
                raise RuntimeError(f"Installed file differs from intended bytes: {rel}")
    except Exception:
        for rel, data in originals.items():
            atomic_write(root / rel, data)
        raise
    print("SUCCESS: ExploreAnywhere Phase 5B Destination Details upgrade installed.")
    print("Updated ONLY: apps/places/views.py, templates/places/place_detail.html")
    print("Preserved: city/publication checks, photo URLs and credit fields, saved-place/itinerary/review/visit workflows,")
    print("           search, recommendations, map provider settings, migrations and database records.")
    print("Backup:", backup.relative_to(root))
    print('To restore: python "' + str(Path(__file__).resolve()) + '" --restore "' + str(backup.relative_to(root)) + '"')
    print("Next: python manage.py check; test Amyan Hill, CPSU Museum, Kabankalan Plaza and Android.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Confirm compatibility; don't write files")
    parser.add_argument("--restore", metavar="BACKUP_DIRECTORY", help="Safely restore a previous Phase 5B backup")
    args = parser.parse_args()
    try:
        root = find_project()
        if args.restore:
            if args.dry_run:
                parser.error("--dry-run and --restore cannot be used together")
            restore(root, args.restore)
            return
        originals, changes = plan(root)
        if changes is None:
            print("ALREADY INSTALLED: Phase 5B template and view are present. No changes needed.")
        elif args.dry_run:
            print("DRY RUN OK: Your Phase 5B files match the uploaded source ZIP.")
            print("Ready to update ONLY: apps/places/views.py, templates/places/place_detail.html")
            print("Improved: responsive hero, authentic gallery, source credits, hobby tags, visitor info,")
            print("          clear actions, existing Google directions, reviews and missing-data states.")
            print("No database, settings, recommendation, or map-provider changes.")
        else:
            install(root, originals, changes)
    except Exception as exc:
        print("STOPPED SAFELY:", exc, file=sys.stderr)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
