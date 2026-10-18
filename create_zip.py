
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parent
output = root / "ExploreAnywhere_Source.zip"

exclude_dirs = {
    ".git", ".venv", "venv", "node_modules",
    "__pycache__", "media", "staticfiles",
    "_trash", ".idea"
}

exclude_names = {
    ".env", "db.sqlite3", "create_zip.py",
    "ExploreAnywhere_Source.zip",
}

count = 0

with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    for file in root.rglob("*"):
        if not file.is_file():
            continue

        relative = file.relative_to(root)

        if any(part in exclude_dirs for part in relative.parts):
            continue

        if file.name in exclude_names:
            continue

        if (
            file.name.startswith(".env.")
            or file.suffix.lower() in {
                ".pyc", ".zip", ".sql", ".sqlite3",
                ".pem", ".key", ".p12", ".pfx"
            }
        ):
            continue

        archive.write(file, relative.as_posix())
        count += 1

print(f"ZIP created: {output}")
print(f"Files included: {count}")
print(f"Size: {output.stat().st_size / 1024 / 1024:.2f} MB")

with ZipFile(output) as archive:
    bad_file = archive.testzip()

if bad_file is None:
    print("ZIP integrity check: PASSED")
else:
    print(f"ZIP integrity check: FAILED ({bad_file})")
