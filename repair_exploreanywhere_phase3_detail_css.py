#!/usr/bin/env python3
"""Fix ExploreAnywhere Phase 3 Place Details CSS rendered as visible text.

Run from the ExploreAnywhere Django project root. Makes a timestamped backup.
Only modifies templates/places/place_detail.html, never the database.
"""
from datetime import datetime
from pathlib import Path
import re
import shutil
import sys

TARGET = Path('templates/places/place_detail.html')
MARKER = '/* ExploreAnywhere phase3 save-and-journey v1 */'


def main():
    if not TARGET.is_file():
        raise RuntimeError('Cannot find templates/places/place_detail.html. Run this command from your project root.')
    original = TARGET.read_text(encoding='utf-8-sig')
    if original.count('{% block extra_css %}') != 1 or original.count('{% block content %}') != 1:
        raise RuntimeError('Unexpected Django template structure. No files changed.')
    css_start = original.index('{% block extra_css %}')
    css_end = original.index('{% endblock %}', css_start)
    css_block = original[css_start:css_end]
    if css_block.count(MARKER) != 1:
        raise RuntimeError('Expected Phase 3 CSS marker was not found exactly once. No files changed.')
    if css_block.count('<style>') != 1 or css_block.count('</style>') != 1:
        raise RuntimeError('Unexpected number of style blocks. No files changed.')
    style_end = css_block.index('</style>')
    marker_position = css_block.index(MARKER)
    if marker_position < style_end:
        print('ALREADY FIXED: The Phase 3 stylesheet is inside the <style> element.')
        return
    trailing_text = css_block[style_end + len('</style>'):]
    # Only move the known auto-generated CSS, and never swallow other content.
    expected_css = re.compile(
        r'^\s*(/\* ExploreAnywhere phase3 save-and-journey v1 \*/\s*'
        r'\.ea-detail-actions \{[^\n]*\}\s*'
        r'\.ea-detail-actions form \{[^\n]*\}\s*'
        r'\.ea-save-action \{[^\n]*\}\s*'
        r'\.ea-save-action\.is-saved \{[^\n]*\}\s*'
        r'\.ea-detail-actions a \{[^\n]*\}\s*'
        r'\.ea-save-status \{[^\n]*\}\s*)$',
        re.S,
    )
    match = expected_css.fullmatch(trailing_text)
    if not match:
        raise RuntimeError('The extra CSS differs from the expected Phase 3 code. No files changed; please send your current detail template.')
    css_to_move = match.group(1).strip()
    patched_css = css_block[:style_end].rstrip() + '\n\n' + css_to_move + '\n</style>\n'
    patched = original[:css_start] + patched_css + original[css_end:]
    if MARKER not in patched or 'ea-detail-actions' not in patched or '{% csrf_token %}' not in patched:
        raise RuntimeError('Could not validate required Save Place UI. No files changed.')
    ts = datetime.now().strftime('%Y%m%d-%H%M%S-%f')
    backup = TARGET.with_name(f'{TARGET.name}.before-phase3-css-fix-{ts}.bak')
    shutil.copy2(TARGET, backup)
    try:
        TARGET.write_text(patched, encoding='utf-8', newline='\n')
    except Exception:
        shutil.copy2(backup, TARGET)
        raise
    print('SUCCESS: Phase 3 Place Details CSS moved inside its <style> element.')
    print('Backup:', backup)
    print('Unchanged: database, Save/Unsave views, Leaflet, MapTiler, Journey dashboard.')
    print('Next: python manage.py shell -c "from django.template.loader import get_template; get_template(\'places/place_detail.html\'); print(\'Template OK\')"')


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print('STOPPED:', exc, file=sys.stderr)
        sys.exit(1)
