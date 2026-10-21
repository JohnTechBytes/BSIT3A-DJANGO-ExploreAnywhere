#!/usr/bin/env python3
"""ExploreAnywhere Phase 6H - backup-safe distance radius filter.

Uses ONLY the latest template supplied in Phase6H ZIP.
Does not include/print/rewrite the existing private map configuration.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime

REL = Path('templates/places/nearby_places.html')
EXPECTED_SHA256 = '72185ce85c0a8f36e0dd7164d59559489eb35f4e7647e64b2749d79287f92da9'
INSTALLED_SHA256 = '18726700b785aba0b5586bea0b87da9e1df58b904dbda3c99e30a8a297c1c011'

def canonical(text):
    return text.replace('\r\n','\n')

def checksum(text):
    return hashlib.sha256(canonical(text).encode('utf-8')).hexdigest()

def replace_once(text, old, new, label):
    n=text.count(old)
    if n!=1: raise RuntimeError(f'{label}: expected one anchor; got {n}')
    return text.replace(old,new,1)

def transform(text):
    # Preserve original line endings by work in canonical LF, encode with caller's original style.
    css='''
/* Phase 6H: location-aware radius filter; existing map tiles and search stay intact. */
.ea6h-radius{display:flex;align-items:end;flex-wrap:wrap;gap:12px;margin:13px 0 0;padding:15px;border:1px solid #d5e5f5;border-radius:13px;background:#f7fbff}
.ea6h-radius .ea6-field{flex:0 1 235px;min-width:min(220px,100%)}
.ea6h-reset{min-height:44px;padding:10px 13px;border:1px solid #bcd4f6;border-radius:10px;background:#fff;color:#1554a8;font:inherit;font-size:13px;font-weight:750;cursor:pointer}
.ea6h-reset:disabled{opacity:.55;cursor:not-allowed}
.ea6h-help{flex:1 1 235px;max-width:100%;font-size:12px;line-height:1.55;color:#426080;padding-bottom:3px}
.ea6h-none{margin:0 0 16px;padding:18px;border:1px dashed #a9c7e9;border-radius:12px;background:#f8fbff;color:#25476d;font-size:13px;line-height:1.6}
.ea6-card[hidden],.ea6h-none[hidden]{display:none!important}
.ea6h-radius select:disabled{background:#eaf0f8;color:#65798e}
.ea6h-reset:focus-visible{outline:3px solid #8ab8ff;outline-offset:3px}
@media(max-width:760px){.ea6h-radius{align-items:stretch}.ea6h-radius .ea6-field,.ea6h-help{flex-basis:100%}.ea6h-reset{width:100%}}
'''
    text=replace_once(text,'</style>',''+css+'</style>','css')
    text=replace_once(text,
'''      <button type="submit" form="ea6-landmark-form" class="ea6-btn ea6-plain">Sort near landmark</button>
    </div>
    <p id="ea6-location-status"''',
'''      <button type="submit" form="ea6-landmark-form" class="ea6-btn ea6-plain">Sort near landmark</button>
    </div>
    <div class="ea6h-radius" aria-label="Filter results by distance">
      <div class="ea6-field">
        <label for="ea6h-distance">Show places within</label>
        <select id="ea6h-distance" disabled aria-describedby="ea6h-distance-help">
          <option value="all">Any distance</option>
          <option value="1">1 km straight-line</option>
          <option value="3">3 km straight-line</option>
          <option value="5">5 km straight-line</option>
          <option value="10">10 km straight-line</option>
          <option value="25">25 km straight-line</option>
        </select>
      </div>
      <button type="button" class="ea6h-reset" id="ea6h-reset" disabled>Clear distance filter</button>
      <span id="ea6h-distance-help" class="ea6h-help" role="status" aria-live="polite">Choose a landmark or enable location permission to filter by distance. This does not use driving routes.</span>
    </div>
    <p id="ea6-location-status"''','distance UI')
    text=replace_once(text,
'<span class="ea6-pill">{{ result_count }} matching listing{{ result_count|pluralize }}</span>',
'<span class="ea6-pill" id="ea6h-result-count">{{ result_count }} matching listing{{ result_count|pluralize }}</span>',
'results count')
    text=replace_once(text,
'''  {% if results %}
    <div class="ea6g-layout" id="ea6g-layout">''',
'''  {% if results %}
    <p id="ea6h-no-results" class="ea6h-none" role="status" hidden>No displayed listings fall within that straight-line distance. Increase the radius or clear the distance filter to see all matches. Listings without recorded coordinates cannot be assessed against a radius.</p>
    <div class="ea6g-layout" id="ea6g-layout">''','empty radius')
    text=replace_once(text,
'''    <div class="ea6-quick"><span>One search for verified businesses and destinations.</span><a href="{% url 'places:attraction_carousel' %}?mode=nearby">Clear search</a></div>''',
'''    <div class="ea6-quick" aria-label="Quick searches for published Kabankalan listings">
      <span>Quick searches:</span>
      <a href="{% url 'places:attraction_carousel' %}?mode=nearby&amp;service=coffee">☕ Coffee</a>
      <a href="{% url 'places:attraction_carousel' %}?mode=nearby&amp;service=restaurant">🍴 Restaurants</a>
      <a href="{% url 'places:attraction_carousel' %}?mode=nearby&amp;service=barber">✂ Barbers</a>
      <a href="{% url 'places:attraction_carousel' %}?mode=nearby&amp;service=mall">🛍 Malls</a>
      <a href="{% url 'places:attraction_carousel' %}?mode=nearby&amp;service=billiards">🎱 Billiards</a>
      <a href="{% url 'places:attraction_carousel' %}?mode=nearby">Clear search</a>
    </div>''','quick categories')
    text=replace_once(text,
'''  const fitButton = document.getElementById("ea6g-fit");''',
'''  const fitButton = document.getElementById("ea6g-fit");
  const distanceSelect = document.getElementById("ea6h-distance");
  const radiusReset = document.getElementById("ea6h-reset");
  const distanceHelp = document.getElementById("ea6h-distance-help");
  const radiusNoResults = document.getElementById("ea6h-no-results");
  const countLabel = document.getElementById("ea6h-result-count");''','js dom')
    anchor='''  function sortNearby(lat, lng, label) {'''
    fn='''  // Phase 6H filters only the already-rendered, staff-verified results.
  // No GPS data is sent to Django, and missing-coordinate results are not
  // silently given a zero distance.
  function visibleMappedRows() { return mappedRows.filter(card => !card.hidden); }
  function radiusAllows(card) {
    if (!originPoint || !distanceSelect || distanceSelect.value === "all") return true;
    if (!mappedRows.includes(card)) return false;
    const lat = Number(card.dataset.lat), lng = Number(card.dataset.lng);
    const radius = Number(distanceSelect.value);
    return haversine(originPoint.lat,originPoint.lng,lat,lng) <= radius + 1e-8;
  }
  function refreshRadius() {
    if (distanceSelect) distanceSelect.disabled = !originPoint;
    const active = !!originPoint && distanceSelect && distanceSelect.value !== "all";
    if (radiusReset) radiusReset.disabled = !active;
    const shown = [];
    rows.forEach(card => {
      card.hidden = !radiusAllows(card);
      if (!card.hidden) shown.push(card);
    });
    const pins = visibleMappedRows();
    if (countLabel) countLabel.textContent = active
      ? shown.length + " of " + rows.length + " matching listings within " + distanceSelect.value + " km"
      : rows.length + " matching listing" + (rows.length === 1 ? "" : "s");
    if (radiusNoResults) radiusNoResults.hidden = shown.length > 0;
    if (distanceHelp) distanceHelp.textContent = active
      ? shown.length + " of " + rows.length + " published listings within " + distanceSelect.value + " km straight-line of " + originPoint.label + ". Listings without coordinates are excluded while this filter is on."
      : originPoint
        ? "Distances are approximate straight-line from " + originPoint.label + ". Select a radius to narrow the results."
        : "Choose a verified landmark or allow GPS to enable distance filtering.";
    if (mapCount) mapCount.textContent = pins.length + " of " + shown.length + " shown listing(s) have recorded map coordinates.";
    if (mapToggle) {
      const open = !!mapShell && !mapShell.hidden;
      mapToggle.disabled = pins.length === 0 && !open;
      mapToggle.textContent = open ? "Hide nearby map"
        : pins.length ? "🗺 View nearby results on map"
        : "Map unavailable for these results";
    }
    if (resultsMap) {
      resultsMapMarkers.forEach((marker,card) => {
        if (card.hidden && resultsMap.hasLayer(marker)) resultsMap.removeLayer(marker);
        else if (!card.hidden && !resultsMap.hasLayer(marker)) marker.addTo(resultsMap);
      });
      selectCard(null);
      if (pins.length) fitResultPins();
      if (mapStatus) mapStatus.textContent = pins.length
        ? pins.length + " mapped listing(s) currently shown; map pins match the distance filter."
        : "No mapped listings within the selected radius. Increase or clear the distance filter.";
    }
  }
  distanceSelect?.addEventListener("change", refreshRadius);
  radiusReset?.addEventListener("click", () => {
    if (distanceSelect) distanceSelect.value = "all";
    refreshRadius();
  });
  function sortNearby(lat, lng, label) {'''
    text=replace_once(text,anchor,fn,'distance logic')
    text=replace_once(text,
'''    originPoint = {lat, lng, label};
    if (resultsMap) { placeOriginMarker(); syncPopupDistances(); }''',
'''    originPoint = {lat, lng, label};
    refreshRadius();
    if (resultsMap) { placeOriginMarker(); syncPopupDistances(); }''','after sort')
    text=replace_once(text,
'''  function selectCard(card) {
    rows.forEach(row => row.classList.toggle("ea6g-selected", row === card));
  }''',
'''  function selectCard(card) {
    rows.forEach(row => row.classList.toggle("ea6g-selected", row === card));
    resultsMapMarkers.forEach((marker,row) => marker.setStyle({
      radius: row === card ? 12 : 9,
      color: row === card ? "#0b3f8f" : "#0757d8",
      fillColor: row === card ? "#f59e0b" : "#0d9488",
      weight: row === card ? 3 : 2
    }));
  }''','pin highlight')
    text=replace_once(text,
'''    const points = mappedRows.map(card => [Number(card.dataset.lat),Number(card.dataset.lng)]);''',
'''    const points = visibleMappedRows().map(card => [Number(card.dataset.lat),Number(card.dataset.lng)]);
    if (!points.length) return;''','map fit')
    text=replace_once(text,
'''    mappedRows.forEach(card => {
      const marker = L.circleMarker([Number(card.dataset.lat),Number(card.dataset.lng)], {''',
'''    visibleMappedRows().forEach(card => {
      const marker = L.circleMarker([Number(card.dataset.lat),Number(card.dataset.lng)], {''','markers initial')
    text=replace_once(text,
'''    if (!mapShell || !mapLayout || !mapToggle || !mappedRows.length) return;''',
'''    if (!mapShell || !mapLayout || !mapToggle || !visibleMappedRows().length) return;''','map open guard')
    text=replace_once(text,
'''      if (mapStatus) mapStatus.textContent = mappedRows.length + " verified location pin(s) shown for these search results. Select a pin or use Show on map on a card.";''',
'''      if (mapStatus) mapStatus.textContent = visibleMappedRows().length + " verified location pin(s) shown for these search results. Select a pin or use Show on map on a card.";''','map status')
    # initialize disabled state on load, for no-origin and map counts
    text=replace_once(text,
'''  gps?.addEventListener("click", function () {''',
'''  refreshRadius();
  gps?.addEventListener("click", function () {''','initialize')
    # prevent older map-open button status if filtered visible count becomes zero and map was already open.
    # limit to UI; no other templates, views or keys touched.
    return text


def read_target(path):
    binary = path.read_bytes()
    return binary.decode('utf-8-sig'), b'\r\n' in binary

def encode_target(text, windows_ending):
    payload = text.replace('\n','\r\n') if windows_ending else text
    return payload.encode('utf-8')

def atomic_write(path, content):
    descriptor, tmp = tempfile.mkstemp(prefix='.ea6h-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor,'wb') as handle:
            handle.write(content)
        os.replace(tmp,path)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)

def run_django(root):
    for args in [
        ['check'],
        ['shell','-c',"from django.template.loader import get_template; get_template('places/nearby_places.html'); print('PASS: Nearby template loads')"],
    ]:
        cmd = [sys.executable, str(root/'manage.py'), *args]
        print('VALIDATING: Django ' + args[0],flush=True)
        result = subprocess.run(cmd, cwd=root, text=True, capture_output=True,timeout=90)
        if result.stdout: print(result.stdout.strip())
        if result.returncode:
            print(result.stderr.strip(),file=sys.stderr)
            raise RuntimeError('Django validation failed; original template must be restored')

def restore(root, backup_str):
    root_resolved = root.resolve()
    folder = (root / backup_str).resolve()
    if root_resolved not in folder.parents:
        raise RuntimeError('Restore backup must be inside the project folder')
    manifest = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    target = root/REL
    original = (folder/'nearby_places.html').read_bytes()
    if hashlib.sha256(original).hexdigest() != manifest['original_bytes_sha256']:
        raise RuntimeError('Backup bytes checksum mismatch')
    present = target.read_bytes()
    if hashlib.sha256(present).hexdigest() != manifest['installed_bytes_sha256']:
        raise RuntimeError('Current template differs from this install; refusing to overwrite newer edits')
    atomic_write(target, original)
    print('RESTORED: Original Nearby template from', folder)
    print('No database records were changed.')

def main():
    parser = argparse.ArgumentParser(description='ExploreAnywhere Phase 6H distance filters (dry run / install / restore)')
    parser.add_argument('--dry-run',action='store_true')
    parser.add_argument('--restore',metavar='BACKUP_DIRECTORY')
    args = parser.parse_args()
    root = Path.cwd().resolve()
    if not (root/'manage.py').is_file():
        raise RuntimeError('Run from your ExploreAnywhere project root containing manage.py')
    if args.restore:
        restore(root,args.restore)
        return
    target=root/REL
    if not target.is_file(): raise RuntimeError('Missing '+str(REL))
    current,crlf=read_target(target)
    digest=checksum(current)
    if digest == INSTALLED_SHA256:
        print('ALREADY INSTALLED: Phase 6H nearby distance filter matches this package.')
        return
    if digest != EXPECTED_SHA256:
        raise RuntimeError('Source mismatch: Nearby template changed since your Phase 6H upload. No changes made. Upload current template before patching.')
    updated=transform(canonical(current))
    if checksum(updated) != INSTALLED_SHA256:
        raise RuntimeError('Safety checksum mismatch in prepared patch. No changes made.')
    if args.dry_run:
        print('DRY RUN OK: Phase 6H distance-range filtering is compatible with the uploaded Nearby template.')
        print('Will update ONLY:',REL)
        print('Preserves: existing MapTiler URLs/key, Leaflet on-demand loading, published-only Django filtering, database, migrations.')
        print('New: radius filter after GPS/landmark, results/map-pin synchronization, active-marker emphasis, quick category shortcuts.')
        return
    original_bytes=target.read_bytes()
    backup=root/'phase6_backups'/('nearby-radius-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True,exist_ok=False)
    (backup/'nearby_places.html').write_bytes(original_bytes)
    patched_bytes=encode_target(updated,crlf)
    manifest={
        'target':str(REL),
        'original_bytes_sha256':hashlib.sha256(original_bytes).hexdigest(),
        'installed_bytes_sha256':hashlib.sha256(patched_bytes).hexdigest(),
    }
    (backup/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print('BACKUP:',backup.relative_to(root),flush=True)
    atomic_write(target,patched_bytes)
    try:
        run_django(root)
    except BaseException:
        atomic_write(target,original_bytes)
        print('VALIDATION FAILED — original template restored from backup. No DB changes.',file=sys.stderr)
        raise
    print('SUCCESS: Phase 6H Nearby distance filter installed.')
    print('Updated ONLY:',REL)
    print('To restore: python',json.dumps(str(Path(__file__).resolve())),'--restore',json.dumps(str(backup.relative_to(root))))
    print('NEXT: Verify distance filters using a verified landmark; test nearby map pins and Android layout.')

if __name__=='__main__':
    try:
        main()
    except Exception as exc:
        print('ERROR:',exc,file=sys.stderr)
        sys.exit(1)
