# OPTIONAL Windows Task Scheduler action - ONLY fetches a preview, never imports.
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $PSScriptRoot
$python = Join-Path $project 'venv\Scripts\python.exe'
$manage = Join-Path $project 'manage.py'
if (-not (Test-Path $python) -or -not (Test-Path $manage)) { throw 'ExploreAnywhere project or venv not found' }
Push-Location $project
try {
    & $python $manage discover_kabankalan_businesses
    if ($LASTEXITCODE -ne 0) { throw 'Discovery failed; check Overpass or the boundary selection.' }
} finally { Pop-Location }
