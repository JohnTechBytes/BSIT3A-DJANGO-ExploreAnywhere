#!/usr/bin/env python3
"""ExploreAnywhere Phase 6N — safe visitor result card polish.
Only modifies templates/places/nearby_places.html and attraction_carousel.html.
No models, database calls of its own, or migrations.
"""
from pathlib import Path
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
import argparse, hashlib, os, subprocess, sys, tempfile

FILES = (
    "templates/places/nearby_places.html",
    "templates/places/attraction_carousel.html",
)
SOURCE_SHA = {
    "templates/places/nearby_places.html": "6e05e44f0742fb0b497687e2b37cd351c1d47746674242ed8601eedf9c169828",
    "templates/places/attraction_carousel.html": "308821b08962203c3e5a463eb350c000e65d3c1ebce0ae25b63fffff4f795ef8",
}
UPDATED_SHA = {
    "templates/places/nearby_places.html": """8dd27e62f6a3a1451cc66a0d36c4ebe3dbf9c93aa7556c31f70f1a133705a2ce""",
    "templates/places/attraction_carousel.html": """e84faa5f37797d5fef602c1b741708da9d30a1e82686e30729d6cd4db684973f""",
}
MARKER = "ExploreAnywhere Phase 6N"

def replace_once(s,old,new,path):
 n=s.count(old)
 if n!=1:raise ValueError(f'{path} expected once, found {n}: {old[:90]!r}')
 return s.replace(old,new,1)

NEAR_CSS = '''
/* ExploreAnywhere Phase 6N: calm, accessible nearby result cards. */
.ea6-card { transition: box-shadow .18s ease, border-color .18s ease; }
@media (hover:hover) and (prefers-reduced-motion:no-preference) {
  .ea6-card:hover { border-color:#b8cfe9; box-shadow:0 13px 30px rgba(15,42,83,.11); }
}
.ea6-cover { height:auto; min-height:0; aspect-ratio:16/9; overflow:hidden; padding:0 16px; }
.ea6-cover img { display:block; width:calc(100% + 32px); max-width:none; height:100%; min-height:0; margin:0 -16px; object-fit:cover; }
.ea6n-no-photo { display:flex; flex-direction:column; justify-content:center; align-items:center; gap:8px; font-size:12px; line-height:1.45; }
.ea6n-no-photo-icon { font-size:29px; line-height:1; }
.ea6n-badges { display:flex; flex-wrap:wrap; align-items:center; gap:7px; }
.ea6n-badges .ea6-category, .ea6n-badges .ea6-public-badge { margin:0; }
.ea6-card-body { gap:10px; padding:19px; }
.ea6-card h3 { font-size:clamp(17px,2vw,19px); line-height:1.35; }
.ea6-card .ea6-description { overflow-wrap:anywhere; }
.ea6-card .ea6-description.ea6n-summary {
  display:-webkit-box; -webkit-line-clamp:3; -webkit-box-orient:vertical;
  overflow:hidden; line-clamp:3;
}
.ea6-card .ea6-distance { margin-top:auto; padding:10px 12px; background:#f0faf5; border:1px solid #d6ebdf; border-radius:10px; line-height:1.45; }
.ea6-card .ea6-actions { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:9px; margin-top:0; padding-top:5px; }
.ea6-card .ea6-actions a, .ea6-card .ea6-actions .ea6g-card-map {
  display:inline-flex; align-items:center; justify-content:center; min-width:0; width:100%;
  min-height:44px; box-sizing:border-box; padding:10px 9px; line-height:1.35; white-space:normal;
  font-size:13px; border-radius:11px; text-align:center; text-decoration:none;
}
.ea6-card .ea6-actions a:first-child { grid-column:auto; }
.ea6-card .ea6-actions a:only-child { grid-column:1/-1; }
.ea6-card .ea6-actions .ea6g-card-map { grid-column:1/-1; margin:0; }
@media (max-width:420px) { .ea6-card-body { padding:16px; } .ea6-card .ea6-actions { gap:8px; } }
@media (prefers-reduced-motion:reduce) { .ea6-card { transition:none; } }
'''

CAR_CSS='''
/* ExploreAnywhere Phase 6N: approachable, thumb-friendly attraction cards. */
.ea-card { transition:box-shadow .18s ease, transform .18s ease; }
.ea-card-image { aspect-ratio:16/9; }
.ea-card-image img { display:block; width:100%; height:100%; object-fit:cover; }
.ea-card-body { gap:0; }
.ea-card .ea-card-description { line-height:1.58; overflow-wrap:anywhere; }
.ea-card .ea-card-footer {
  display:grid; grid-template-columns:repeat(2,minmax(0,1fr));
  align-items:stretch; gap:9px; margin-top:auto; padding-top:15px;
}
.ea-card-footer .ea-map-link {
  display:inline-flex !important; justify-content:center; align-items:center;
  width:100%; min-width:0; min-height:44px; box-sizing:border-box;
  margin:0 !important; padding:10px 12px; border-radius:11px;
  border:1px solid #bcd4f6; background:#f0f6ff; color:#0757d8;
  text-decoration:none; text-align:center; font-size:13px; font-weight:800; line-height:1.3;
}
.ea-card-footer .ea-map-link.ea6n-primary {
  color:#fff; background:#0757d8; border-color:#0757d8;
}
.ea-card-footer .ea-map-link.ea6n-primary:hover { color:#fff; background:#0649b3; }
.ea-card-footer .ea-map-link:not(.ea6n-primary):hover { background:#e0efff; text-decoration:none; }
.ea-card-footer .ea-map-link:focus-visible { outline:3px solid #87b9ff; outline-offset:2px; }
.ea-card-footer .ea6n-map-unavailable { grid-column:1/-1; text-align:center; margin:0; font-size:12px; }
.ea-card-footer .ea-map-link:only-child { grid-column:1/-1; }
@media(max-width:420px) {
  .ea-card-body { padding:17px; }
  .ea-card-footer .ea-map-link { padding:10px 8px; }
}
@media(hover:hover) and (prefers-reduced-motion:no-preference) {
  .ea-card:hover { transform:translateY(-2px); }
}
@media(prefers-reduced-motion:reduce) { .ea-card { transition:none; } }
'''

def patch_nearby(s):
 # inline stylesheet closes immediately before content block; keep all JS as-is.
 s=replace_once(s,'</style>\n{% endblock %}\n{% block content %}',NEAR_CSS+'\n</style>\n{% endblock %}\n{% block content %}','nearby: CSS')
 s=replace_once(s,'<img loading="lazy" decoding="async" alt="{{ place.title }}" src="{{ place.cover_image.url }}">','<img loading="lazy" decoding="async" width="640" height="360" alt="{{ place.title }}" src="{{ place.cover_image.url }}">','nearby: local photo')
 s=replace_once(s,'<img loading="lazy" decoding="async" alt="{{ place.title }}" src="{{ place.cover_image_url }}">','<img loading="lazy" decoding="async" width="640" height="360" alt="{{ place.title }}" src="{{ place.cover_image_url }}">','nearby: remote photo')
 s=replace_once(s,'<span aria-label="No verified destination photograph">📍 Genuine photo not available yet</span>', '<span class="ea6n-no-photo" role="img" aria-label="No verified photograph available"><span class="ea6n-no-photo-icon" aria-hidden="true">📷</span><span>Photo not yet available</span></span>', 'nearby: placeholder')
 s=replace_once(s,'''            <span class="ea6-category">{% if place.category %}{{ place.category.name }}{% else %}Place in Kabankalan{% endif %}</span>
            <span class="ea6-public-badge" title="Reviewed and published by ExploreAnywhere staff">✓ Staff verified listing</span>''','''            <div class="ea6n-badges">
              <span class="ea6-category">{% if place.category %}{{ place.category.name }}{% else %}Place in Kabankalan{% endif %}</span>
              <span class="ea6-public-badge" title="Reviewed and published by ExploreAnywhere staff">✓ Staff verified listing</span>
            </div>''','nearby: tags')
 s=replace_once(s,'<p class="ea6-description">{% if place.description %}{{ place.description|truncatechars:125 }}{% else %}Detailed information is not yet available.{% endif %}</p>','<p class="ea6-description ea6n-summary">{% if place.description %}{{ place.description|truncatechars:125 }}{% else %}Detailed information is not yet available.{% endif %}</p>','nearby: summary')
 return s

def patch_carousel(s):
 s=replace_once(s,'</style>\n{% endblock %}',CAR_CSS+'\n</style>\n{% endblock %}','carousel: CSS')
 for url in ['{{ place.cover_image.url }}','{{ place.cover_image_url }}']:
  s=replace_once(s,'''                  src="'''+url+'''"
                  alt="{{ place.title }}"
                  loading="lazy"
                  decoding="async"
''','''                  src="'''+url+'''"
                  alt="{{ place.title }}"
                  loading="lazy"
                  decoding="async"
                  width="640"
                  height="360"
''','carousel: photo')
 old='''              <div class="ea-card-footer">
                <a
    class="ea-map-link"
    href="{% url 'places:place_detail' place.pk %}"
    style="display:inline-block;margin-bottom:12px;"
>
    View Details &#8594;
</a>
                {% if place.latitude != None and place.longitude != None %}
                  <a
                    class="ea-map-link"
                    href="https://www.google.com/maps/search/?api=1&amp;query={{ place.latitude }},{{ place.longitude }}"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    View on Map &#8599;
                  </a>
                {% else %}
                  <span class="ea-card-location">
                    Map location unavailable
                  </span>
                {% endif %}
              </div>'''
 new='''              <div class="ea-card-footer">
                <a class="ea-map-link ea6n-primary" href="{% url 'places:place_detail' place.pk %}">View Details →</a>
                {% if place.latitude != None and place.longitude != None %}
                  <a class="ea-map-link" href="https://www.google.com/maps/dir/?api=1&amp;destination={{ place.latitude }},{{ place.longitude }}" target="_blank" rel="noopener noreferrer" aria-label="Directions to {{ place.title }} (opens Google Maps)">Directions ↗</a>
                {% else %}
                  <span class="ea-card-location ea6n-map-unavailable">Map location unavailable</span>
                {% endif %}
              </div>'''
 s=replace_once(s,old,new,'carousel: footer')
 return s

def normalized_bytes(path):
    data=path.read_bytes()
    bom=data.startswith(b"\xef\xbb\xbf")
    try:
        decoded=data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise RuntimeError(f"{path}: not UTF-8 ({error})") from error
    newline="\r\n" if b"\r\n" in data else "\n"
    text=decoded.replace("\r\n","\n").replace("\r","\n")
    return data,text,newline,bom

def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()

def encode_text(content,newline,bom):
    return (("\ufeff" if bom else "")+content.replace("\n",newline)).encode("utf-8")

def atomic_write(path,content):
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(dir=str(path.parent),prefix=".ea6n_",delete=False) as f:
            temporary=Path(f.name)
            f.write(content)
        os.replace(str(temporary),str(path))
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()

def django_check(root):
    checks=[
       ([sys.executable,"manage.py","check"],"Django system check"),
       ([sys.executable,"manage.py","shell","-c",
         "from django.template.loader import get_template; "
         "[get_template(n) for n in ('places/nearby_places.html', 'places/attraction_carousel.html')]; "
         "print('TEMPLATE CHECK OK: 2 templates compiled')"],"Django template compilation"),
    ]
    for cmd,label in checks:
        try:
            proc=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=90)
        except (OSError,subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"{label} unavailable: {exc}") from exc
        if proc.stdout.strip():print(proc.stdout.strip())
        if proc.returncode:
            raise RuntimeError(f"{label} failed: {(proc.stderr or proc.stdout).strip()[-3500:]}")

def find_root():
    root=Path.cwd().resolve()
    if not (root/"manage.py").is_file():
        raise RuntimeError("Open a VS Code terminal at the ExploreAnywhere project root (containing manage.py).")
    return root

def restore(root,archive):
    if not archive.is_file():raise RuntimeError(f"Backup ZIP not found: {archive}")
    # Manual restoration should not silently overwrite work done since 6N.
    for rel in FILES:
        target=root/rel
        if target.exists():
            _,current,_,_=normalized_bytes(target)
            if digest(current) not in (SOURCE_SHA[rel],UPDATED_SHA[rel]):
                raise RuntimeError(f"Refusing restore: {rel} has changed since Phase 6N. Back it up and review first.")
    with ZipFile(archive) as z:
        if set(z.namelist())!=set(FILES):
            raise RuntimeError("Backup must contain exactly the two expected templates; not restored.")
        recovered={rel:z.read(rel) for rel in FILES}
    for rel,data in recovered.items():
        atomic_write(root/rel,data)
        print(f"RESTORED: {rel}")
    print("RESTORE OK: original templates written from the selected backup.")

def main():
    parser=argparse.ArgumentParser(description="Phase 6N — result card polish and safer action layout")
    parser.add_argument("--dry-run",action="store_true")
    parser.add_argument("--restore",type=Path,metavar="BACKUP_ZIP")
    args=parser.parse_args()
    root=find_root()
    if args.restore:
        restore(root,args.restore.resolve());return
    transforms={
        FILES[0]:patch_nearby,
        FILES[1]:patch_carousel,
    }
    originals={};patched={};states={}
    for rel in FILES:
        path=root/rel
        if not path.is_file():raise RuntimeError(f"Missing required file: {rel}")
        raw,source,newline,bom=normalized_bytes(path)
        sha=digest(source)
        if sha==UPDATED_SHA[rel]:
            states[rel]="installed"
            print(f"ALREADY INSTALLED: {rel}")
            continue
        if sha!=SOURCE_SHA[rel]:
            raise RuntimeError(f"SOURCE MISMATCH: {rel} differs from the uploaded Phase 6N source. No files changed. Upload your newest template(s) rather than forcing an overwrite.")
        modified=transforms[rel](source)
        if digest(modified)!=UPDATED_SHA[rel]:
            raise RuntimeError(f"Internal patch verification failed for {rel}. No files changed.")
        originals[rel]=raw
        patched[rel]=encode_text(modified,newline,bom)
        states[rel]="ready"
        print(f"READY: {rel}")
    if all(s=="installed" for s in states.values()):
        print("ALREADY INSTALLED: no files changed.");return
    if set(states.values())!={"ready"}:
        raise RuntimeError("PARTIAL INSTALL detected; no files changed. Inspect the files before trying again.")
    if args.dry_run:
        print("DRY RUN OK: both templates match your uploaded source; no files changed.")
        return
    backups=root/"phase6_backups"
    backups.mkdir(exist_ok=True)
    archive=backups/("phase6n_cards_"+datetime.now().strftime("%Y%m%d_%H%M%S_%f")+".zip")
    with ZipFile(archive,"x",ZIP_DEFLATED) as z:
        for rel in FILES:z.writestr(rel,originals[rel])
    print(f"BACKUP: {archive}")
    try:
        for rel in FILES:atomic_write(root/rel,patched[rel])
        django_check(root)
    except Exception:
        failures=[]
        for rel in FILES:
            try:atomic_write(root/rel,originals[rel])
            except Exception as e:failures.append(f"{rel}: {e}")
        if failures:
            print("URGENT: rollback incomplete: "+"; ".join(failures),file=sys.stderr)
        else:
            print("ROLLBACK OK: original templates restored; backup kept.",file=sys.stderr)
        raise
    print("INSTALL OK: cards polished; no models, migrations, or database changes.")
    print(f'TO RESTORE: python "{Path(__file__).resolve()}" --restore "{archive}"')

if __name__=="__main__":
    try:main()
    except Exception as exc:
        print(f"ERROR: {exc}",file=sys.stderr)
        sys.exit(1)
