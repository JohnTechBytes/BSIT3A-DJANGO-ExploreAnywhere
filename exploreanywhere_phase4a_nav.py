#!/usr/bin/env python3
"""ExploreAnywhere Phase 4A: guarded, backup-safe template navigation update.
Run from the Django project root. No changes to database, models, views or API keys.
"""
from pathlib import Path
from datetime import datetime
import shutil
import sys

ROOT = Path.cwd()
BASE = ROOT / 'templates' / 'theme' / 'public_base.html'
HOME = ROOT / 'templates' / 'home.html'

SHARED_LINKS = '''        <div class="ea-nav-links" id="public-nav-links">
            <a href="{% url 'home' %}">Home</a>
            <a href="{% url 'hobbies:select' %}">Explore Places</a>
            <a href="{% url 'hobbies:select' %}">Hobbies</a>
            {% if request.user.is_authenticated %}
                <a href="{% url 'places:saved_places' %}">Saved Places</a>
                <a href="{% url 'places:journey_dashboard' %}">My Journey</a>
                <details class="ea-nav-more">
                    <summary>More <span aria-hidden="true">&#9662;</span></summary>
                    <div class="ea-nav-submenu">
                        <a href="{% url 'itineraries:list' %}">My Itineraries</a>
                        <a href="{% url 'places:my_reviews' %}">My Reviews</a>
                        <a href="{% url 'visits:list' %}">My Visits</a>
                    </div>
                </details>
            {% endif %}
        </div>
'''

BASE_ACTIONS = '''        <div class="ea-nav-actions">
            {% if request.user.is_authenticated %}
                {% if request.user.is_staff %}
                    <a href="{% url 'admin:index' %}" class="ea-nav-btn ea-nav-outline">Staff Dashboard</a>
                {% endif %}
                <form method="post" action="{% url 'logout' %}" class="ea-nav-logout-form">
                    {% csrf_token %}
                    <button type="submit" class="ea-nav-btn ea-nav-primary">Logout</button>
                </form>
            {% else %}
                <a href="{% url 'login' %}" class="ea-nav-btn ea-nav-outline">Login</a>
                <a href="{% url 'register' %}" class="ea-nav-btn ea-nav-primary">Sign Up</a>
            {% endif %}
        </div>
'''

BASE_CSS = '''
        /* ExploreAnywhere Phase 4A: shared visitor navigation */
        .ea-nav-links { gap: 18px; }
        .ea-nav-links a { font-size: 13px; }
        .ea-nav-more { position: relative; color: #cbd5e1; font-size: 13px; font-weight: 600; }
        .ea-nav-more summary { list-style: none; cursor: pointer; padding: 10px 0; border-bottom: 2px solid transparent; }
        .ea-nav-more summary::-webkit-details-marker { display: none; }
        .ea-nav-more summary:hover, .ea-nav-more[open] summary { color: #fff; border-color: #3b82f6; }
        .ea-nav-submenu { position: absolute; top: 100%; right: 0; min-width: 175px; padding: 8px; background: #142748; border: 1px solid #35547c; border-radius: 12px; box-shadow: 0 12px 30px rgba(0,0,0,.22); z-index: 80; }
        .ea-nav-submenu a { display: block; padding: 9px 12px; border: 0; border-radius: 7px; }
        .ea-nav-submenu a:hover { background: #1e3a63; }
        .ea-nav-logout-form { margin: 0; }
        .ea-nav-btn { cursor: pointer; font-family: inherit; }
        .ea-mobile-menu:focus-visible, .ea-nav-more summary:focus-visible, .ea-nav-links a:focus-visible, .ea-nav-actions a:focus-visible, .ea-nav-btn:focus-visible { outline: 3px solid #93c5fd; outline-offset: 3px; }
        @media (max-width: 1150px) and (min-width: 901px) {
            .ea-nav-container { gap: 12px; padding-inline: 16px; }
            .ea-nav-links { gap: 10px; }
            .ea-nav-links a, .ea-nav-more { font-size: 12px; }
            .ea-site-logo { font-size: 18px; }
            .ea-nav-btn { padding: 9px 12px; font-size: 12px; }
        }
        @media (max-width: 900px) {
            .ea-nav-links { align-items: stretch; }
            .ea-nav-more summary { padding: 12px 8px; }
            .ea-nav-submenu { position: static; min-width: auto; box-shadow: none; margin-top: 4px; }
            .ea-site-header.menu-open .ea-nav-actions { flex-direction: column; align-items: stretch; gap: 8px; }
            .ea-nav-logout-form, .ea-nav-logout-form button { width: 100%; }
            .ea-nav-actions .ea-nav-btn { width: 100%; }
        }
'''

HOME_NAV = '''<nav class="navbar navbar-expand-lg sticky-top" aria-label="Main navigation">
    <div class="container">
        <a class="brand" href="{% url 'home' %}">
            <div class="brand-icon" aria-hidden="true">&#8982;</div>
            <span>Explore<span>Anywhere</span></span>
        </a>
        <button class="navbar-toggler" type="button"
                data-bs-toggle="collapse" data-bs-target="#mainNav"
                aria-controls="mainNav" aria-expanded="false"
                aria-label="Toggle navigation">
            <span class="navbar-toggler-icon"></span>
        </button>
        <div class="collapse navbar-collapse" id="mainNav">
            <div class="navbar-nav ms-auto align-items-lg-center gap-lg-2 ea-home-nav-links">
                <a class="nav-link" href="{% url 'home' %}">Home</a>
                <a class="nav-link" href="{% url 'hobbies:select' %}">Explore Places</a>
                <a class="nav-link" href="{% url 'hobbies:select' %}">Hobbies</a>
                <a class="nav-link" href="#how-it-works">About</a>
                {% if user.is_authenticated %}
                    <a class="nav-link" href="{% url 'places:saved_places' %}">Saved</a>
                    <a class="nav-link" href="{% url 'places:journey_dashboard' %}">My Journey</a>
                    <div class="dropdown ea-home-more">
                        <button class="nav-link dropdown-toggle btn" type="button"
                                data-bs-toggle="dropdown" aria-expanded="false">More</button>
                        <ul class="dropdown-menu dropdown-menu-end">
                            <li><a class="dropdown-item" href="{% url 'itineraries:list' %}">My Itineraries</a></li>
                            <li><a class="dropdown-item" href="{% url 'places:my_reviews' %}">My Reviews</a></li>
                            <li><a class="dropdown-item" href="{% url 'visits:list' %}">My Visits</a></li>
                        </ul>
                    </div>
                    {% if user.is_staff %}
                        <a class="btn-outline-custom ms-lg-1" href="{% url 'admin:index' %}">Staff Dashboard</a>
                    {% endif %}
                    <form method="post" action="{% url 'logout' %}" class="ea-home-logout ms-lg-1">
                        {% csrf_token %}
                        <button type="submit" class="btn-primary-custom">Logout</button>
                    </form>
                {% else %}
                    <a class="nav-link" href="{% url 'login' %}">Login</a>
                    <a class="btn-primary-custom ms-lg-1" href="{% url 'register' %}">Sign Up</a>
                {% endif %}
            </div>
        </div>
    </div>
</nav>'''

HOME_CSS = '''
/* ExploreAnywhere Phase 4A: consistent and accessible main navigation */
.navbar .ea-home-nav-links .dropdown > button.nav-link {
    color: #e2e8f0 !important; border: 0; background: transparent !important;
    font-size: 13px; font-weight: 600; box-shadow: none; padding: 9px 8px;
}
.navbar .ea-home-nav-links .dropdown-menu {
    border: 1px solid #dce6f3; border-radius: 12px;
    box-shadow: 0 14px 32px rgba(0,0,0,.16); padding: 8px;
}
.navbar .ea-home-nav-links .dropdown-menu a.dropdown-item {
    color: #183456 !important; font-size: 13px; border-radius: 6px; padding: 10px 12px;
}
.navbar .ea-home-nav-links .dropdown-menu a.dropdown-item:hover { background: #eff6ff; }
.navbar .ea-home-logout { margin-bottom: 0; }
.navbar .ea-home-logout button { cursor: pointer; font-size: 13px; padding: 10px 14px; }
.navbar .ea-home-nav-links > .nav-link { font-size: 13px; }
.navbar .ea-home-nav-links .btn-outline-custom,
.navbar .ea-home-nav-links .btn-primary-custom { font-size: 13px; padding: 10px 13px; }
.navbar :is(a,button):focus-visible { outline: 3px solid #93c5fd !important; outline-offset: 3px; }
@media (max-width: 1199px) and (min-width: 992px) {
    .navbar .container { max-width: 98%; }
    .navbar .brand { font-size: 18px; }
    .navbar .ea-home-nav-links { gap: 4px !important; }
    .navbar .ea-home-nav-links > .nav-link { font-size: 12px; padding-inline: 5px; }
    .navbar .ea-home-logout button { padding: 9px 10px; }
}
@media (max-width: 991px) {
    .navbar .ea-home-logout, .navbar .ea-home-logout button { width: 100%; }
    .navbar .ea-home-nav-links .dropdown-menu { position: static !important; box-shadow: none; }
    .navbar .ea-home-nav-links .dropdown > button.nav-link { width: 100%; text-align: left; padding: 10px 12px; }
}
'''


def replace_exact(s, needle, replacement, name):
    count = s.count(needle)
    if count != 1:
        raise ValueError(f'{name}: expected exactly one matching section, found {count}. Files not modified.')
    return s.replace(needle, replacement, 1)


def plan_base(raw):
    if 'ExploreAnywhere Phase 4A:' in raw:
        raise ValueError('public_base.html already appears patched; refusing to apply twice.')
    if '<div class="ea-nav-actions">' not in raw or 'id="public-nav-links"' in raw:
        raise ValueError('Shared navbar is different from the reviewed template. No changes made.')
    start = raw.index('        <div class="ea-nav-actions">')
    end = raw.index('\n\n    </nav>', start)
    region = raw[start:end]
    for marker in ('Explore Cities', 'action="/accounts/logout/"', '{% csrf_token %}'):
        if marker not in region:
            raise ValueError(f'Expected shared nav marker missing: {marker}')
    raw = raw[:start] + SHARED_LINKS + '\n' + BASE_ACTIONS.rstrip() + raw[end:]
    raw = replace_exact(raw, '    </style>\n\n    {% block extra_css %}', BASE_CSS + '    </style>\n\n    {% block extra_css %}', 'Shared CSS placement')
    raw = replace_exact(raw, '        <span>Find places. Live the vibe.</span>', '        <span>One City. Your Hobbies. Our Map.</span>', 'Shared footer')
    return raw


def plan_home(raw):
    if 'ExploreAnywhere Phase 4A:' in raw:
        raise ValueError('home.html already appears patched; refusing to apply twice.')
    start_marker = '<nav class="navbar navbar-expand-lg sticky-top">'
    if raw.count(start_marker) != 1:
        raise ValueError('Homepage navbar anchor not found uniquely; no changes made.')
    start = raw.index(start_marker)
    end = raw.index('</nav>', start) + len('</nav>')
    original = raw[start:end]
    for marker in ('id="mainNav"', 'action="{% url \'logout\' %}"', 'href="{% url \'register\' %}"'):
        if marker not in original:
            raise ValueError(f'Homepage navbar differs from reviewed template: {marker}')
    raw = raw[:start] + HOME_NAV + raw[end:]
    # Insert CSS immediately before the closing stylesheet, never as visible page text.
    css_end = raw.index('</style>')
    raw = raw[:css_end] + HOME_CSS + raw[css_end:]
    # Only update active landing-page copy and inert CTAs; leave app logic alone.
    raw = raw.replace('Discover places that match your hobbies in any city.',
                      'Discover Kabankalan destinations that match your hobbies.')
    raw = raw.replace('Explore cities, compare nearby venues, and make',
                      'Discover Kabankalan destinations, compare local venues, and make')
    raw = raw.replace('Explore your hobbies, discover new cities,',
                      'Explore your hobbies, discover Kabankalan,')
    raw = raw.replace('Start with Kabankalan and expand to more\n                            cities without rebuilding the application.',
                      'Discover verified destinations around Kabankalan\n                            through hobbies, maps, and local experiences.')
    raw = raw.replace('<h3>Explore Any City</h3>', '<h3>Explore Kabankalan</h3>')
    raw = raw.replace('href="{{ city_url|default:\'#hobbies\' }}"', 'href="{% url \'hobbies:select\' %}"')
    return raw


def main():
    for f in (BASE, HOME):
        if not f.is_file():
            sys.exit(f'ERROR: File missing: {f}. Run script from Django project root.')
    base_original = BASE.read_text(encoding='utf-8-sig')
    home_original = HOME.read_text(encoding='utf-8-sig')
    try:
        planned = {BASE: plan_base(base_original), HOME: plan_home(home_original)}
    except (ValueError, IndexError) as ex:
        sys.exit('SAFETY STOP: ' + str(ex))
    backup_dir = ROOT / 'phase4_backups' / ('navbar-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    backup_dir.mkdir(parents=True, exist_ok=False)
    for file in (BASE, HOME):
        backup = backup_dir / file.relative_to(ROOT)
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, backup)
    written = []
    try:
        for file, value in planned.items():
            file.write_text(value, encoding='utf-8', newline='')
            written.append(file)
    except Exception:
        for file in written:
            shutil.copy2(backup_dir / file.relative_to(ROOT), file)
        raise
    print('SUCCESS: ExploreAnywhere Phase 4A navigation installed.')
    print('Updated: templates/theme/public_base.html and templates/home.html')
    print('Backup:', backup_dir.relative_to(ROOT))
    print('Navigation: Home, Explore Places, Hobbies, Saved Places, My Journey, Itineraries, Reviews, Visits.')
    print('Authenticated users: POST Logout. Staff: Staff Dashboard.')
    print('No models, migrations, API keys, or database records modified.')
    print('NEXT: python manage.py check')
    print('NEXT: python manage.py shell -c "from django.template.loader import get_template; [get_template(t) for t in [\'home.html\',\'theme/public_base.html\']]; print(\'Templates OK\')"')

if __name__ == '__main__':
    main()
