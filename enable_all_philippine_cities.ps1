
# ==============================================
# ExploreAnywhere - Enable All Philippine Cities
# No database migrations required
# ==============================================

$ErrorActionPreference = "Stop"

if (!(Test-Path "manage.py")) {
    throw "Run this from the ExploreAnywhere project root."
}

$patcher = "_patch_city_selectability.py"

$pythonCode = @'
from pathlib import Path
from datetime import datetime
import re
import shutil

views_path = Path("apps/cities/views.py")
js_path = Path("static/js/city_select.js")

for path in (views_path, js_path):
    if not path.exists():
        raise SystemExit(f"Missing file: {path}")

def read(path):
    return path.read_text(encoding="utf-8-sig")

views = read(views_path)
js = read(js_path)

# ---------------------------------------
# 1. Allow active AND pending cities
# ---------------------------------------

match = re.search(
    r"(?m)^def choose_city\(request\):",
    views
)

if not match:
    raise SystemExit(
        "Could not find choose_city() in views.py. "
        "No files changed."
    )

start = match.start()

next_function = re.search(
    r"(?m)^def \w+\(",
    views[match.end():]
)

end = (
    match.end() + next_function.start()
    if next_function else len(views)
)

before = views[:start]
function = views[start:end]
after = views[end:]

# Remove status restriction only from
# choose_city(), not other views.

function, removed = re.subn(
    r'(?m)^[ \t]*status\s*=\s*["\']active["\'],[ \t]*\n',
    "",
    function,
    count=1
)

if removed != 1:
    raise SystemExit(
        "Active-only restriction not found in "
        "choose_city(). No files changed."
    )

views = before + function + after

# Restore pending city selections on reload.
views = re.sub(
    r'filter\(pk=selected_id,\s*status=["\']active["\']\)',
    'filter(pk=selected_id)',
    views
)

# ---------------------------------------
# 2. Make pending city cards clickable
# ---------------------------------------

js, disabled_removed = re.subn(
    r'if\s*\(!active\)\s*\{\s*'
    r'button\.disabled\s*=\s*true;\s*'
    r'button\.classList\.add\(["\']pending["\']\);\s*'
    r'\}',
    '',
    js,
    count=1
)

if disabled_removed != 1:
    raise SystemExit(
        "Pending-card disable block not found. "
        "No files changed."
    )

# Change click handler from active-only
# to all city cards.

js, listener_changed = re.subn(
    r'if\s*\(active\)\s*\{\s*'
    r'(button\.addEventListener\(["\']click["\'],\s*'
    r'\(\)\s*=>\s*\{\s*setSelected\(city\);\s*\}\);)'
    r'\s*\}',
    r'\1',
    js,
    count=1
)

if listener_changed != 1:
    raise SystemExit(
        "Active-only card listener not found. "
        "No files changed."
    )

# ---------------------------------------
# 3. Update availability labels
# ---------------------------------------

js = re.sub(
    r'badge\.textContent\s*=\s*active\s*\?\s*'
    r'["\']Active["\']\s*:\s*["\']Pending["\'];',
    'badge.textContent = active ? "Active" : "No places yet";',
    js,
    count=1
)

js, places_changed = re.subn(
    r'places\.textContent\s*=\s*active\s*\?'
    r'\s*`\$\{city\.places_count\} places`'
    r'\s*:\s*["\']Coming soon["\'];',
    'places.textContent = `${city.places_count} places available`;',
    js,
    count=1
)

if places_changed != 1:
    raise SystemExit(
        "Place-count display not found. "
        "No files changed."
    )

# ---------------------------------------
# 4. Back up and save updated files
# ---------------------------------------

stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

for path, content in [
    (views_path, views),
    (js_path, js),
]:
    backup = path.with_name(
        path.name + ".bak_" + stamp
    )

    shutil.copy2(path, backup)
    path.write_text(content, encoding="utf-8")

    print(f"UPDATED: {path}")
    print(f"BACKUP:  {backup}")

print()
print("All cities can now be selected.")
print("Pending status remains in the database.")
print("No migrations or data updates performed.")
'@

try {
    [System.IO.File]::WriteAllText(
        (Join-Path (Get-Location).Path $patcher),
        $pythonCode,
        [System.Text.UTF8Encoding]::new($false)
    )

    python $patcher

    if ($LASTEXITCODE -ne 0) {
        throw "Patch failed. Read the message above."
    }

    Write-Host "`nChecking Django..." -ForegroundColor Cyan
    python manage.py check

    if ($LASTEXITCODE -ne 0) {
        throw "Django check failed. Review the generated backups."
    }

    Write-Host "`nSUCCESS!" -ForegroundColor Green
    Write-Host "Open: http://127.0.0.1:8000/cities/select/"
}
finally {
    if (Test-Path $patcher) {
        Remove-Item $patcher -Force
    }
}
