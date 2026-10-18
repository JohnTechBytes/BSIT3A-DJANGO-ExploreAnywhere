"""ExploreAnywhere: enrich imported OSM attractions with exact Wikidata P18 images.

Place this file at apps/places/management/commands/enrich_attraction_photos.py.

Preview: python manage.py enrich_attraction_photos --limit 20
Apply:   python manage.py enrich_attraction_photos --limit 20 --apply
Next:    python manage.py enrich_attraction_photos --offset 20 --limit 20 --apply

Requires WIKIMEDIA_USER_AGENT in the environment and certifi installed.
"""
import csv
import html
import json
import os
import re
import ssl
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote, urlsplit
from urllib.request import Request, urlopen

import certifi
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils.html import strip_tags
from apps.places.models import Place

SOURCE = Path(settings.BASE_DIR) / 'data/osm/extracted/philippines_attractions_nodes.csv'
REPORT_DIR = Path(settings.BASE_DIR) / 'data/osm/validation'
LICENSES = {
    'CC BY 4.0', 'CC BY 3.0', 'CC BY-SA 4.0', 'CC BY-SA 3.0', 'CC0 1.0',
}


def trusted_url(value, allowed_hosts):
    try:
        parsed = urlsplit(value)
        return (parsed.scheme == 'https' and parsed.hostname in allowed_hosts
                and not parsed.username and not parsed.password)
    except (ValueError, TypeError):
        return False


def request_json(url, user_agent, context):
    request = Request(url, headers={
        'User-Agent': user_agent,
        'Accept': 'application/json',
    })
    with urlopen(request, timeout=35, context=context) as response:
        return json.load(response)


def wikidata_image(qid, user_agent, context):
    url = 'https://www.wikidata.org/wiki/Special:EntityData/' + qid + '.json'
    data = request_json(url, user_agent, context)
    entity = data.get('entities', {}).get(qid, {})
    for claim in entity.get('claims', {}).get('P18', []):
        value = claim.get('mainsnak', {}).get('datavalue', {}).get('value')
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def commons_photo(filename, user_agent, context):
    params = urlencode({
        'action': 'query', 'format': 'json', 'prop': 'imageinfo',
        'titles': 'File:' + filename.removeprefix('File:'),
        'iiprop': 'url|extmetadata', 'iiurlwidth': '960',
    })
    data = request_json('https://commons.wikimedia.org/w/api.php?' + params,
                        user_agent, context)
    for page in data.get('query', {}).get('pages', {}).values():
        for info in page.get('imageinfo', []):
            ext = info.get('extmetadata', {})
            def val(key):
                return str(ext.get(key, {}).get('value') or '')
            artist = html.unescape(strip_tags(val('Artist'))).strip()
            if not artist:
                artist = html.unescape(strip_tags(val('Attribution'))).strip()
            photo = {
                'image_url': info.get('thumburl') or info.get('url') or '',
                'photo_source_url': info.get('descriptionurl') or '',
                'photo_credit': re.sub(r'\s+', ' ', artist)[:500],
                'photo_license': val('LicenseShortName').strip(),
                'photo_license_url': val('LicenseUrl').strip(),
            }
            return photo
    return None


class Command(BaseCommand):
    help = 'Preview/apply authentic Wikimedia images tied to exact OSM Wikidata IDs.'

    def add_arguments(self, parser):
        parser.add_argument('--offset', type=int, default=0)
        parser.add_argument('--limit', type=int, default=20)
        parser.add_argument('--apply', action='store_true',
                            help='Save approved metadata without changing existing photos.')

    def handle(self, *args, **options):
        offset, limit = options['offset'], options['limit']
        if offset < 0 or not 1 <= limit <= 100:
            raise CommandError('Use --offset >= 0 and --limit between 1 and 100.')
        if not SOURCE.is_file():
            raise CommandError(f'Missing source: {SOURCE}')
        agent = os.environ.get('WIKIMEDIA_USER_AGENT', '').strip()
        if not agent or 'example.com' in agent or 'your-email' in agent:
            raise CommandError('Set WIKIMEDIA_USER_AGENT with a real contact address.')

        required = ('cover_image_url', 'photo_credit', 'photo_source_url',
                    'photo_license', 'photo_license_url')
        missing = [f for f in required if not hasattr(Place, f)]
        if missing:
            raise CommandError(f'Missing Place fields: {missing}')
        max_lengths = {
            key: Place._meta.get_field(key).max_length
            for key in required
        }
        context = ssl.create_default_context(cafile=certifi.where())
        osm_tags = {}
        with SOURCE.open(encoding='utf-8-sig', newline='') as fh:
            for row in csv.DictReader(fh):
                try:
                    tags = json.loads(row.get('tags_json') or '{}')
                except (TypeError, ValueError):
                    continue
                if isinstance(tags, dict):
                    qid = str(tags.get('wikidata') or '').strip()
                    if re.fullmatch(r'Q[1-9]\d*', qid):
                        osm_tags[row.get('osm_id')] = qid
        places = list(Place.objects.filter(slug__in=osm_tags)
                      .order_by('pk').values('pk', 'slug', 'title', 'cover_image',
                                              'cover_image_url'))
        candidates = [(p, osm_tags[p['slug']]) for p in places]
        selection = candidates[offset:offset + limit]
        self.stdout.write(f'Imported Wikidata-linked attractions: {len(candidates)}')
        self.stdout.write(f'Checking {len(selection)} (offset {offset}, limit {limit})')
        found, saved, skipped, failed = 0, 0, 0, 0
        report = []
        for index, (p, qid) in enumerate(selection, start=offset + 1):
            if p['cover_image'] or p['cover_image_url']:
                skipped += 1
                self.stdout.write(f'[{index}] SKIP existing image: {p["title"]}')
                continue
            try:
                filename = wikidata_image(qid, agent, context)
                if not filename:
                    self.stdout.write(f'[{index}] No P18 image: {p["title"]}')
                    continue
                time.sleep(0.6)
                photo = commons_photo(filename, agent, context)
                if not photo:
                    self.stdout.write(f'[{index}] No Commons metadata: {p["title"]}')
                    continue
                reasons = []
                if photo['photo_license'] not in LICENSES:
                    reasons.append('license needs review')
                if not photo['photo_credit']:
                    reasons.append('missing author')
                if not trusted_url(photo['image_url'],
                                   {'upload.wikimedia.org', 'thumb.wikimedia.org'}):
                    reasons.append('untrusted image URL')
                if not trusted_url(photo['photo_source_url'], {'commons.wikimedia.org'}):
                    reasons.append('untrusted source URL')
                if not trusted_url(photo['photo_license_url'], {'creativecommons.org'}):
                    reasons.append('untrusted license URL')
                
                if any(
                    max_lengths[k]
                    and len(
                        photo[
                            'image_url'
                            if k == 'cover_image_url'
                            else k
                        ]
                    ) > max_lengths[k]
                    for k in required
                ):
                    reasons.append(
                        'exceeds database field length'
                    )

                # Conservative destination identity check.
                # A Wikidata P18 image can depict a related place,
                # rather than the actual attraction.
                import unicodedata

                def words(value):
                    value = unicodedata.normalize("NFKD", value)
                    value = "".join(
                        ch for ch in value
                        if not unicodedata.combining(ch)
                    ).casefold()
                    return re.findall(r"[a-z0-9]+", value)

                generic = {
                    "mount", "mountain", "mt", "hill",
                    "peak", "city", "of", "the", "a",
                    "and", "at", "in", "philippines",
                }

                destination_words = [
                    word for word in words(p["title"])
                    if word not in generic and len(word) >= 4
                ]

                image_words = words(filename)
                image_text = "".join(image_words)

                identity_match = (
                    bool(destination_words)
                    and all(
                        word in image_words or word in image_text
                        for word in destination_words
                    )
                )

                if not identity_match:
                    reasons.append(
                        "destination filename mismatch - "
                        "manual identity review required"
                    )

                record = {'osm_id': p['slug'], 'name': p['title'], 'wikidata': qid,
                          'filename': filename, **photo,
                          'status': 'REVIEW: ' + '; '.join(reasons) if reasons else 'ELIGIBLE'}
                report.append(record)
                if reasons:
                    skipped += 1
                    self.stdout.write(f'[{index}] REVIEW {p["title"]}: {", ".join(reasons)}')
                    continue
                found += 1
                self.stdout.write(f'[{index}] PHOTO {p["title"]}: {photo["photo_license"]}')
                if options['apply']:
                    with transaction.atomic():
                        updated = (Place.objects.filter(pk=p['pk'])
                                   .filter(Q(cover_image='') | Q(cover_image__isnull=True))
                                   .filter(Q(cover_image_url='') | Q(cover_image_url__isnull=True))
                                   .update(cover_image_url=photo['image_url'],
                                           photo_credit=photo['photo_credit'],
                                           photo_source_url=photo['photo_source_url'],
                                           photo_license=photo['photo_license'],
                                           photo_license_url=photo['photo_license_url']))
                    saved += updated
            except (HTTPError, URLError, TimeoutError, OSError, ValueError,
                    json.JSONDecodeError) as error:
                failed += 1
                self.stderr.write(f'[{index}] API error {p["title"]}: {error}')
            time.sleep(0.6)
        REPORT_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORT_DIR / f'photo_enrichment_{offset}_{limit}.csv'
        fields = ('osm_id', 'name', 'wikidata', 'filename', 'image_url',
                  'photo_source_url', 'photo_credit', 'photo_license',
                  'photo_license_url', 'status')
        with report_path.open('w', encoding='utf-8-sig', newline='') as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(report)
        self.stdout.write(f'Eligible: {found}; saved: {saved}; skipped/review: {skipped}; API errors: {failed}')
        self.stdout.write(f'Report: {report_path}')
        self.stdout.write('APPLIED to blank-photo records only.' if options['apply']
                          else 'PREVIEW ONLY: Database unchanged.')
