
from pathlib import Path
import ast
import shutil

path = Path("apps/places/views.py")
source = path.read_text(encoding="utf-8-sig")

try:
    ast.parse(source)
    print("SUCCESS: views.py already has valid Python syntax.")
    raise SystemExit(0)
except SyntaxError as error:
    print(f"Detected: {error.msg} at line {error.lineno}")

lines = source.splitlines(keepends=True)

# Only repair an incomplete render() context at the
# end of place_detail(), not arbitrary Python syntax.
detail_start = source.rfind("\ndef place_detail(")

if detail_start == -1:
    print("Automatic repair stopped: place_detail() not found.")
    raise SystemExit(1)

detail_section = source[detail_start:]

if '"places/place_detail.html"' not in detail_section:
    print("Automatic repair stopped: detail render not found.")
    raise SystemExit(1)

# Try appending missing render/dictionary closers.
# Never save a candidate unless it passes AST validation.
candidates = [
    "\n        },\n    )\n",
    "\n        }\n    )\n",
    "\n    )\n",
    "\n}\n)\n",
]

for suffix in candidates:
    candidate = source.rstrip() + suffix

    try:
        ast.parse(candidate)
    except SyntaxError:
        continue

    backup = path.with_suffix(".py.before-repair.bak")
    shutil.copy2(path, backup)
    path.write_text(candidate, encoding="utf-8")

    print("SUCCESS: Missing closing syntax repaired.")
    print("Backup:", backup)
    raise SystemExit(0)

print("Automatic repair could not safely determine the correction.")
print("Original file has not been modified.")
print("Please inspect the code near the reported line.")
raise SystemExit(1)
