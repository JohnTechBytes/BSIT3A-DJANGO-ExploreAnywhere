# ExploreAnywhere Phase 6O.6: guarded template-only patch installation.
# No Django management commands or database writes occur in this script.
param(
    [string]$ProjectRoot = (Get-Location).Path
)
$ErrorActionPreference = 'Stop'

$project = (Resolve-Path -LiteralPath $ProjectRoot).Path
$bundle = Split-Path -Parent $PSCommandPath
$manifestPath = Join-Path $bundle 'MANIFEST.json'
$manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
$names = @('nearby_places.html', 'attraction_carousel.html', 'saved_places.html')

if (-not (Test-Path -LiteralPath (Join-Path $project 'manage.py') -PathType Leaf)) {
    throw 'This is not the ExploreAnywhere Django project folder: manage.py is missing.'
}

# Preflight: refuse to overwrite templates modified since the supplied review ZIP.
foreach ($name in $names) {
    $entry = $manifest.PSObject.Properties[$name].Value
    $target = Join-Path $project (Join-Path 'templates\places' $name)
    $replacement = Join-Path $bundle (Join-Path 'templates\places' $name)
    if (-not (Test-Path -LiteralPath $target -PathType Leaf)) { throw "Missing original template: $target" }
    if (-not (Test-Path -LiteralPath $replacement -PathType Leaf)) { throw "Missing patch template: $replacement" }
    $current = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
    $expected = [string]$entry.original_sha256
    if ($current -ne $expected) {
        throw "Template differs from the uploaded review copy: $name. No files changed. Request a refreshed patch."
    }
    $patched = (Get-FileHash -LiteralPath $replacement -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($patched -ne [string]$entry.patched_sha256) { throw "Patch checksum mismatch: $name. No files changed." }
}

$backup = Join-Path $project ('phase6o_frontend_backup_' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
New-Item -ItemType Directory -Path $backup -ErrorAction Stop | Out-Null
foreach ($name in $names) {
    $original = Join-Path $project (Join-Path 'templates\places' $name)
    Copy-Item -LiteralPath $original -Destination (Join-Path $backup $name) -ErrorAction Stop
}

try {
    foreach ($name in $names) {
        $entry = $manifest.PSObject.Properties[$name].Value
        $target = Join-Path $project (Join-Path 'templates\places' $name)
        $replacement = Join-Path $bundle (Join-Path 'templates\places' $name)
        Copy-Item -LiteralPath $replacement -Destination $target -Force -ErrorAction Stop
        $after = (Get-FileHash -LiteralPath $target -Algorithm SHA256).Hash.ToLowerInvariant()
        if ($after -ne [string]$entry.patched_sha256) { throw "Post-copy checksum mismatch: $name" }
    }
} catch {
    foreach ($name in $names) {
        Copy-Item -LiteralPath (Join-Path $backup $name) -Destination (Join-Path $project (Join-Path 'templates\places' $name)) -Force -ErrorAction Stop
    }
    throw "Patch failed and backup copies were restored: $($_.Exception.Message)"
}

Write-Host 'PHASE 6O.6: Three frontend templates installed.' -ForegroundColor Green
Write-Host "Original template backup: $backup"
Write-Host 'Django models, migrations, review CSV, and MySQL have not been changed.'
Write-Host 'NEXT: python manage.py check'
Write-Host "NEXT: python manage.py shell -c `"from django.template.loader import get_template; [get_template('places/'+n) for n in ('nearby_places.html','attraction_carousel.html','saved_places.html')]; print('Template parse OK')`""
Write-Host 'NEXT: python manage.py phase6o_business_photos --apply-approved --dry-run'
