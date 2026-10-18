"""Repair ExploreAnywhere Kabankalan homepage navbar only.

Run from the Django project root:
    python repair_exploreanywhere_nav.py
"""

from datetime import datetime
from pathlib import Path
import re
import sys

path = Path('templates/home.html')
if not path.is_file():
    sys.exit('ERROR: Run this from your ExploreAnywhere project root (where manage.py is).')

original_bytes = path.read_bytes()
try:
    source = original_bytes.decode('utf-8-sig')
except UnicodeDecodeError:
    sys.exit('ERROR: Homepage is not UTF-8; no changes made.')

nav = re.search(r'<div\s+class=["\']navbar-nav\s+ms-auto[^"\']*["\']\s*>', source)
if not nav:
    sys.exit('ERROR: Could not find the existing navbar links container. No changes made.')

close = source.find('</div>', nav.end())
if close == -1:
    sys.exit('ERROR: Could not locate navbar closing div. No changes made.')

current_nav = source[nav.end():close]
if '<div' in current_nav:
    sys.exit('ERROR: Nested div found inside navbar; refusing an unsafe replacement. No changes made.')

start = source.find('{% if user.is_authenticated %}', nav.end(), close)
if start == -1:
    sys.exit('ERROR: Authentication block not found in navbar. No changes made.')

correct_auth = '''                {% if user.is_authenticated %}
                    {% if user.is_staff %}
                        <a class="btn-outline-custom ms-lg-2"
                           href="{% url 'admin:index' %}">Dashboard</a>
                    {% else %}
                        <a class="btn-outline-custom ms-lg-2"
                           href="{% url 'hobbies:select' %}">Explore Places</a>
                    {% endif %}
                    <form method="post" action="{% url 'logout' %}"
                          class="d-inline-block ms-lg-2">
                        {% csrf_token %}
                        <button type="submit" class="btn-outline-custom"
                                style="cursor:pointer;">Logout</button>
                    </form>
                {% else %}
                    <a class="nav-link" href="{% url 'login' %}">Login</a>
                    <a class="btn-primary-custom ms-lg-2"
                       href="{% url 'register' %}">Sign Up</a>
                {% endif %}
'''

fixed = source[:start] + correct_auth + source[close:]

# Remove only a loose, standalone Django URL tag that prints "/hobbies/"
# above the page. Do not remove attributes or real navigation links.
fixed, stray_count = re.subn(
    r'(?m)^[ \t]*{%\s*url\s+["\']hobbies:select["\']\s*%}[ \t]*\r?\n',
    '', fixed,
)

if fixed == source:
    print('No changes required.')
    sys.exit(0)

backup = path.with_name('home.html.pre-navbar-fix-' + datetime.now().strftime('%Y%m%d-%H%M%S') + '.bak')
backup.write_bytes(original_bytes)
path.write_bytes(fixed.encode('utf-8'))

print('SUCCESS: Homepage navbar template repaired.')
print('Auth: Login / Sign Up when logged out; Dashboard or Explore Places + Logout when logged in.')
print('Standalone hobby URL tags removed:', stray_count)
print('Backup:', backup)
print('Next: python manage.py shell -c "from django.template.loader import get_template; get_template(\'home.html\'); print(\'Homepage OK\')"')
