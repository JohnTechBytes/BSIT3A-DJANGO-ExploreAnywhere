
import argparse
import shutil
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Archive folder is OUTSIDE the Django project.
ARCHIVE = (
    ROOT.parent
    / "ExploreAnywhere_Archive"
    / datetime.now().strftime("%Y%m%d_%H%M%S")
)

# Old standalone scripts from the nationwide project.
LEGACY_SCRIPTS = [
    "extract_philippines_attractions.py",
    "extract_all_philippines_attractions.py",
    "match_philippines_attractions.py",
    "match_attractions_by_province.py",
    "resolve_unique_city_matches.py",
    "validate_full_adm3.py",
    "import_validated_attractions.py",
    "check_province_mismatches.py",
    "check_attraction_photo_sources.py",
    "repair_wikimedia_command.py",
    "test_wikimedia_connection.py",
]

# Do not remove Django apps, migrations, settings, templates,
# static files, databases, or source datasets.
PROTECTED = {
    "apps",
    "mysite",
    "templates",
    "static",
    "media",
    "data",
    "manage.py",
    "requirements.txt",
    ".env",
    ".git",
    "venv",
    ".venv",
    "venv_old",
    "db.sqlite3",
}

def candidates(include_legacy=False):
    found = set()

    # Previous editing/repair backup files.
    for pattern in ("*.bak", "*.backup"):
        for path in ROOT.rglob(pattern):
            if any(
                part in {
                    ".git", "venv", ".venv", "venv_old",
                    "node_modules"
                }
                for part in path.relative_to(ROOT).parts
            ):
                continue

            if path.is_file():
                found.add(path)

    # Compiled Python caches can safely be regenerated.
    for path in ROOT.rglob("__pycache__"):
        if any(
            part in {".git", "venv", ".venv", "venv_old"}
            for part in path.relative_to(ROOT).parts
        ):
            continue

        if path.is_dir():
            found.add(path)

    if include_legacy:
        for name in LEGACY_SCRIPTS:
            path = ROOT / name
            if path.is_file():
                found.add(path)

    return sorted(found, key=lambda p: str(p))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply", action="store_true"
    )
    parser.add_argument(
        "--include-legacy", action="store_true"
    )
    args = parser.parse_args()

    items = candidates(args.include_legacy)

    print("\nEXPLOREANYWHERE PROJECT CLEANUP")
    print("=" * 45)
    print("Mode:", "ARCHIVE" if args.apply else "PREVIEW")
    print("Files/folders found:", len(items))

    for path in items:
        print("  ", path.relative_to(ROOT))

    if not args.apply:
        print("\nNo changes made.")
        print("Use --apply to move these items to an archive.")
        return

    if not items:
        print("Nothing to archive.")
        return

    # Prevent moving files inside an already selected folder.
    selected = []
    for path in items:
        if not any(
            parent in selected for parent in path.parents
        ):
            selected.append(path)

    moved = 0

    for path in selected:
        relative = path.relative_to(ROOT)

        # Never archive protected top-level content.
        if relative.parts[0] in PROTECTED:
            continue

        destination = ARCHIVE / relative
        destination.parent.mkdir(
            parents=True, exist_ok=True
        )

        shutil.move(str(path), str(destination))
        moved += 1

    print("\nArchived:", moved)
    print("Archive location:", ARCHIVE)
    print("Nothing was permanently deleted.")


if __name__ == "__main__":
    main()
