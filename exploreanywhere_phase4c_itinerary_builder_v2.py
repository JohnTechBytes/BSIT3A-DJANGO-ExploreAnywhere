#!/usr/bin/env python3
"""ExploreAnywhere Phase 4C+ -- Responsive Itinerary Builder UI redesign.

Run inside the ExploreAnywhere project folder:
    python "<Downloads>/exploreanywhere_phase4c_itinerary_builder_v2.py"

Changes only templates/itineraries/builder.html. Preserves all Django POST
forms, CSRF tags, URL names, data model, and existing views.
"""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

TARGET = Path('templates/itineraries/builder.html')
EXPECTED_SHA256 = '17d9b18eddf439b6c4beb2c4da7d21afa31f3eced5a722a206cf9bff967a2d44'
MARKER = '/* exploreanywhere-builder-v2-20261016 */'

CSS = r'''
/* exploreanywhere-builder-v2-20261016 */
/* Presentation only: existing URLs, forms, controls and user data are unchanged. */
.ea-trip {
  width:100%; max-width:1320px; margin-inline:auto;
  padding:36px clamp(18px,3.2vw,44px) 100px;
  font-size:15px; line-height:1.55;
  --trip-blue:#0864df; --trip-navy:#102d55; --trip-border:#dce6f3;
  --trip-muted:#526985;
}
.ea-trip * {box-sizing:border-box; min-width:0}
.ea-trip .hero {
  position:relative;overflow:hidden;
  display:flex; flex-direction:column; justify-content:center;
  min-height:206px; padding:clamp(30px,4vw,50px);
  border-radius:24px;
  background:radial-gradient(circle at 88% 16%,rgba(132,210,255,.36),transparent 30%),
  linear-gradient(110deg,#0b2850 0%,#0a4ca5 54%,#116ee9 100%);
  box-shadow:0 18px 42px rgba(7,54,117,.15);
}
.ea-trip .hero:after {
  content:""; pointer-events:none; position:absolute; right:-30px;bottom:-100px;
  width:340px;height:340px;border:1px solid rgba(255,255,255,.16);
  border-radius:50%;box-shadow:0 0 0 53px rgba(255,255,255,.035),0 0 0 105px rgba(255,255,255,.026);
}
.ea-trip .hero > *{position:relative;z-index:1}
.ea-trip .hero h1{font-size:clamp(29px,3.2vw,44px);line-height:1.15;letter-spacing:-.035em;font-weight:850;margin:9px 0 9px;color:#fff}
.ea-trip .hero p{font-size:14px;color:#e5efff}
.ea-trip .hero p:first-child{font-size:12px;letter-spacing:.13em;text-transform:uppercase;color:#cce4ff;font-weight:800}
.ea-trip .ea-trip-hero-stats{display:flex;gap:10px;flex-wrap:wrap;margin-top:23px}
.ea-trip .ea-trip-hero-stats span{
  display:inline-flex;align-items:center;gap:6px;border:1px solid rgba(222,238,255,.3);
  border-radius:999px;background:rgba(255,255,255,.13);color:#fff;
  font-size:12px;font-weight:650;padding:7px 13px;
}
.ea-trip .ea-trip-hero-stats strong{font-size:14px;color:white}
.ea-trip .actions[aria-label="Itinerary navigation"]{margin:20px 0 26px;gap:10px}
.ea-trip .btn{
  display:inline-flex;align-items:center;justify-content:center;gap:7px;
  font-size:14px;line-height:1.2;font-weight:750;min-height:45px;
  padding:11px 17px;border-radius:12px;white-space:normal;text-align:center;
}
.ea-trip .actions[aria-label="Itinerary navigation"] .btn{background:#fff;border-color:#cbdcf0;color:#195394!important}
.ea-trip .actions[aria-label="Itinerary navigation"] .btn:hover{background:#eaf4ff}
.ea-trip .grid{
  display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1fr);
  align-items:stretch;gap:22px;margin-top:6px;margin-bottom:35px;
}
.ea-trip .grid >.panel{margin:0;min-height:100%;}
.ea-trip .panel{
  padding:clamp(22px,2.7vw,32px);border-radius:20px;
  border:1px solid var(--trip-border);background:#fff;
  box-shadow:0 9px 26px rgba(21,53,91,.065);
}
.ea-trip .panel h2{font-size:21px;font-weight:850;color:var(--trip-navy);letter-spacing:-.02em;margin:0 0 20px}
.ea-trip .grid>.panel>form{display:flex;flex-direction:column;gap:3px;}
.ea-trip .grid>.panel>form>.btn{align-self:flex-start;margin-top:7px}
.ea-trip .grid>.panel .field{margin-bottom:14px}
.ea-trip .field label{display:block;font-size:13px;line-height:1.35;color:#25466a;font-weight:750;margin-bottom:3px}
.ea-trip input,.ea-trip select,.ea-trip textarea{
  width:100%;background:#fff;color:#122e53;
  border:1px solid #bbcee6;border-radius:12px;
  min-height:46px;padding:11px 13px;font-size:14px;
}
.ea-trip input:focus,.ea-trip select:focus,.ea-trip textarea:focus{border-color:var(--trip-blue);box-shadow:0 0 0 4px rgba(8,100,223,.11);outline:none}
.ea-trip .grid .muted{margin:16px 0 0;font-size:13px;background:#f1f7ff;border-radius:10px;padding:10px 12px}
.ea-trip .ea-trip-stops-header{display:flex;align-items:end;justify-content:space-between;gap:16px;flex-wrap:wrap;margin:3px 0 18px}
.ea-trip .ea-trip-stops-header h2{font-size:25px;font-weight:850;letter-spacing:-.02em;color:var(--trip-navy);margin:0}
.ea-trip .ea-trip-stops-header p{margin:4px 0 0;font-size:13px;color:var(--trip-muted)}
.ea-trip .ea-trip-stops-count{background:#eaf3ff;color:#075cc5;border:1px solid #cddfff;border-radius:999px;padding:7px 13px;font-weight:750;font-size:12px}
.ea-trip .trip-cards{display:grid;grid-template-columns:minmax(0,1fr);gap:18px;margin-bottom:27px}
.ea-trip .stop{
  display:grid;grid-template-columns:minmax(0,.83fr) minmax(0,1.17fr);
  grid-template-areas:"head form" "location form" "actions actions";
  gap:10px 30px;margin:0;padding:25px 28px;
  border-left:0;border-top:0;border-radius:20px;
  border:1px solid #dce6f3;
  box-shadow:0 9px 24px rgba(17,49,85,.06);
  position:relative;overflow:hidden;
}
.ea-trip .stop:before{content:"";position:absolute;inset:0 auto 0 0;width:5px;background:linear-gradient(#0a5cdc,#55b7ff)}
.ea-trip .stop>.stop-head{grid-area:head;display:flex;align-items:flex-start;justify-content:space-between;gap:12px;margin:0}
.ea-trip .stop>.stop-head h3{font-size:21px;line-height:1.25;margin:12px 0 0;color:#14365d}
.ea-trip .stop>.muted{grid-area:location;margin:0;align-self:start;font-size:13px}
.ea-trip .stop>.stop-head .mini-actions{flex:none;display:flex;gap:7px}
.ea-trip .stop>.stop-head .mini-actions .btn{width:44px;min-width:44px;padding:8px;font-size:18px}
.ea-trip .stop>.stop-head .mini-actions form{margin:0}
.ea-trip .stop>.stop-head .pill{background:#e8f2ff;color:#0a5cc5;font-size:12px;padding:6px 12px}
.ea-trip .stop>form{
  grid-area:form;display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);
  align-content:start;gap:10px 14px;
}
.ea-trip .stop>form .field{margin:0}
.ea-trip .stop>form>button{grid-column:1/-1;justify-self:start;margin-top:2px}
.ea-trip .stop>.actions{
  grid-area:actions;margin:13px 0 0;padding:17px 0 0;border-top:1px solid #edf1f7;
  display:flex;flex-wrap:wrap;gap:9px;align-items:center;
}
.ea-trip .stop>.actions .btn{min-height:43px}
.ea-trip .stop>.actions .btn.danger{background:#fff7f7;border-color:#e8bdc3;color:#ae3049!important}
.ea-trip .stop>.actions .btn.danger:hover{background:#ffe9ed}
.ea-trip .empty{padding:34px;border:1px dashed #a9c7eb;background:#f7fbff;border-radius:18px}
.ea-trip .empty h2{font-size:22px;color:var(--trip-navy)}
.ea-trip>section.panel:last-of-type{margin-top:30px;background:#fffdfd;border-color:#efd6da}
.ea-trip>section.panel:last-of-type h2{color:#8d2740;margin-bottom:10px}
.ea-trip>section.panel:last-of-type p{max-width:72ch;margin-bottom:18px}
.ea-trip>section.panel:last-of-type .btn.danger{color:#ab2c43!important;border-color:#e6b8c2;background:#fff7f8}
.ea-trip :is(a,button,input,select,textarea):focus-visible{outline:3px solid #efa62c;outline-offset:3px}
@media(max-width:1000px){
  .ea-trip .stop{grid-template-columns:minmax(0,1fr);grid-template-areas:"head" "location" "form" "actions";gap:14px}
  .ea-trip .stop>form{margin-top:4px}
}
@media(max-width:760px){
  .ea-trip{padding:23px 15px 78px}
  .ea-trip .hero{min-height:0;padding:29px 23px;border-radius:18px}
  .ea-trip .hero:after{display:none}
  .ea-trip .grid{grid-template-columns:minmax(0,1fr);gap:15px}
  .ea-trip .panel,.ea-trip .stop{padding:20px;border-radius:16px}
  .ea-trip .trip-cards{grid-template-columns:1fr}
  .ea-trip .ea-trip-stops-header h2{font-size:22px}
  .ea-trip .stop>form{grid-template-columns:minmax(0,1fr)}
  .ea-trip .stop>form>button{grid-column:1}
  .ea-trip .actions[aria-label="Itinerary navigation"] .btn{flex:1 1 auto}
  .ea-trip .stop>.actions .btn{flex:1 1 auto}
  .ea-trip .stop>.stop-head h3{font-size:19px}
}
@media(max-width:380px){
  .ea-trip .stop>.stop-head{flex-wrap:wrap}
  .ea-trip .stop>.stop-head .mini-actions{width:100%}
  .ea-trip .stop>.actions form{width:100%}
  .ea-trip .stop>.actions .btn{width:100%}
}
@media(prefers-reduced-motion:reduce){
  .ea-trip .btn{transition:none}
  .ea-trip .btn:hover{transform:none}
}
'''

HERO_BEFORE = '''  <div class="hero"><p>MY KABANKALAN JOURNEY · TRIP PLANNER</p><h1>{{ trip.title }}</h1><p>Day {{ trip.day_number }} · Kabankalan, Negros Occidental</p></div>'''
HERO_AFTER = '''  <div class="hero">
    <p>MY KABANKALAN JOURNEY · TRIP PLANNER</p>
    <h1>{{ trip.title }}</h1>
    <p>Build your Kabankalan itinerary. Organize stops, arrival times and notes in one place.</p>
    <div class="ea-trip-hero-stats" aria-label="Itinerary summary">
      <span>Day <strong>{{ trip.day_number }}</strong></span>
      <span><strong>{{ stops|length }}</strong> planned stop{{ stops|length|pluralize }}</span>
      <span>Kabankalan, Negros Occidental</span>
    </div>
  </div>'''

STOPS_BEFORE = '''  <section aria-label="Scheduled itinerary stops"><h2>Your Planned Stops ({{ stops|length }})</h2>'''
STOPS_AFTER = '''  <section aria-label="Scheduled itinerary stops">
    <div class="ea-trip-stops-header">
      <div>
        <h2>Your Planned Stops</h2>
        <p>Update times and notes, or use the arrows to change the stop order.</p>
      </div>
      <span class="ea-trip-stops-count">{{ stops|length }} stop{{ stops|length|pluralize }}</span>
    </div>'''


def unique_replace(text: str, old: str, new: str, name: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Unexpected {name}: found {count} matches (expected 1)")
    return text.replace(old, new, 1)


def transform(original: str) -> str:
    if MARKER in original:
        return original
    updated = unique_replace(original, '</style>', CSS + '\n</style>', 'stylesheet closing tag')
    updated = unique_replace(updated, HERO_BEFORE, HERO_AFTER, 'original hero')
    updated = unique_replace(updated, STOPS_BEFORE, STOPS_AFTER, 'planned stops heading')
    # Prevent silent form/tag/route alterations; all server-backed behavior stays identical.
    for token in ('method="post"', '{% csrf_token %}', 'onsubmit=', 'name="direction"',
                  'name="place_id"', 'name="start_time"', 'name="notes"',
                  'itineraries:delete', 'itineraries:move_stop', 'itineraries:update_stop',
                  'itineraries:add_stop', 'itineraries:update'):
        if original.count(token) != updated.count(token):
            raise ValueError('Existing functionality changed unexpectedly: ' + token)
    before_tags = re.findall(r'{%.*?%}', original, flags=re.S)
    after_tags = re.findall(r'{%.*?%}', updated, flags=re.S)
    if before_tags != after_tags:
        raise ValueError('Django logic tags changed unexpectedly')
    if original.count('<form') != updated.count('<form') or original.count('</form>') != updated.count('</form>'):
        raise ValueError('Form count mismatch')
    return updated


def main() -> int:
    cwd = Path.cwd().resolve()
    if not (cwd / 'manage.py').is_file():
        print('ERROR: Open the ExploreAnywhere project folder (containing manage.py) first.')
        return 1
    target = cwd / TARGET
    if not target.is_file():
        print('ERROR: Missing', TARGET)
        return 1
    raw = target.read_bytes()
    try:
        src = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        print('STOPPED: Template is not UTF-8. No changes made.')
        return 1
    if MARKER in src:
        print('ALREADY INSTALLED: Itinerary Builder V2 is present. No files changed.')
        return 0
    if hashlib.sha256(raw).hexdigest() != EXPECTED_SHA256:
        print('STOPPED SAFELY: Itinerary Builder differs from the Phase 4C template used to test this fix.')
        print('No files changed. Upload your latest templates/itineraries/builder.html for a tailored update.')
        return 1
    try:
        result = transform(src).encode('utf-8')
    except ValueError as e:
        print('STOPPED SAFELY:', e)
        return 1
    if '--check' in sys.argv:
        print('READY: The itinerary template is compatible. No files modified.')
        return 0
    backup = cwd / 'phase4_backups' / ('itinerary-builder-v2-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup.mkdir(parents=True, exist_ok=False)
    backup_target = backup / 'builder.html'
    backup_target.write_bytes(raw)
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(mode='wb', dir=target.parent, prefix='.builder-v2-', suffix='.tmp', delete=False) as f:
            temp_name = f.name
            f.write(result)
        os.replace(temp_name, target)
    except Exception as exc:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
        shutil.copy2(backup_target, target)
        print('ERROR: Unable to install; restored original template.', exc)
        return 1
    print('SUCCESS: Phase 4C+ Itinerary Builder V2 redesigned.')
    print('Updated:', TARGET)
    print('Backup:', backup.relative_to(cwd))
    print('Preserved: 7 POST/CSRF forms, URL names, actions, stop management, Django models and database records.')
    print('No migrations needed.')
    print('Next: python manage.py check')
    print('Next: python manage.py shell -c "from django.template.loader import get_template; get_template(\'itineraries/builder.html\'); print(\'Builder Template OK\')"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
