"""Safe, limited patch for ExploreAnywhere recommendation template.
Run from Django project root with the script stored in Downloads.
Only changes labels, and optionally adds a Leaflet hobby-match legend.
"""
from pathlib import Path
from datetime import datetime
import re
import sys

TARGET = Path('templates/places/attraction_carousel.html')
if not TARGET.is_file():
    sys.exit('ERROR: Cannot find templates/places/attraction_carousel.html. Run from your Django project root.')

old = TARGET.read_text(encoding='utf-8-sig')
new = old
changes = []

# Replace mojibake ONLY in known visible action labels, leaving Django/JS untouched.
for label, entity in [('View Details', '&#8594;'), ('Get Directions', '&#8599;')]:
    pattern = re.compile(r'(?m)^([ \t]*)(' + re.escape(label) + r')([^\r\n]*)(\r?)$')
    def fix(match):
        tail = match.group(3)
        if any(c in tail for c in ('Ã', 'Â', 'â', '�')):
            changes.append('Repaired broken ' + label + ' label')
            return match.group(1) + match.group(2) + ' ' + entity + match.group(4)
        return match.group(0)
    new = pattern.sub(fix, new)

# Make visible match scores explain what they measure: selected hobbies, not semantic search.
old_badge = '{{ place.match_percent }}% Match'
new_badge = '{{ place.match_percent }}% Hobby Match'
if old_badge in new:
    new = new.replace(old_badge, new_badge)
    changes.append('Clarified card badge: Hobby Match')

# Add accessible, compact legend using existing marker thresholds. Avoid changing MapTiler setup.
legend_tag = 'ea-hobby-match-legend-v1'
marker_hook = re.compile(r'(?m)^(\s*)attractions\.forEach\(\(attraction\s*,\s*index\)\s*=>\s*\{')
if legend_tag not in new:
    match = marker_hook.search(new)
    if match:
        indent = match.group(1)
        snippet = f'''{indent}// {legend_tag}: color thresholds match markerColor below.
{indent}const hobbyLegend = L.control({{ position: "bottomleft" }});
{indent}hobbyLegend.onAdd = function () {{
{indent}  const el = L.DomUtil.create("div", "ea-hobby-match-legend");
{indent}  el.setAttribute("role", "note");
{indent}  el.setAttribute("aria-label", "Hobby match marker legend");
{indent}  el.style.cssText = "background:rgba(255,255,255,.96);padding:9px 11px;border-radius:10px;box-shadow:0 2px 10px rgba(0,0,0,.14);font:12px/1.6 Arial,sans-serif;color:#17304f;max-width:160px;";
{indent}  el.innerHTML = '<strong>Hobby match</strong><div><span style="color:#16a34a">●</span> 80–100% High</div><div><span style="color:#f59e0b">●</span> 50–79% Medium</div><div><span style="color:#dc2626">●</span> 0–49% Low</div>';
{indent}  L.DomEvent.disableClickPropagation(el);
{indent}  return el;
{indent}}};
{indent}hobbyLegend.addTo(map);

'''
        new = new[:match.start()] + snippet + new[match.start():]
        changes.append('Added Leaflet map marker-color legend')
    else:
        print('INFO: Legend not added (marker loop not found); existing map remains unchanged.')
else:
    print('INFO: Legend already installed.')

if new == old:
    print('No changes needed. The template was already repaired or did not contain matching patterns.')
    sys.exit(0)

stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
backup = TARGET.with_name(f'{TARGET.name}.pre-recommendation-ui-{stamp}.bak')
backup.write_text(old, encoding='utf-8')
TARGET.write_text(new, encoding='utf-8')
print('Updated:', TARGET)
print('Backup:', backup)
for description in changes:
    print('OK:', description)
print('Next: python manage.py shell -c "from django.template.loader import get_template; get_template(\'places/attraction_carousel.html\'); print(\'Template OK\')"')
print('Then: python manage.py check')
