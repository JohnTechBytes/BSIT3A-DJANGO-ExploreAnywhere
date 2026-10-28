"""ExploreAnywhere Phase 6P.4: Kabankalan-only human-reviewed LOCAL cover photos.

Standalone additive management command; no model/schema/template changes.
--inventory creates/refreshes a REVIEW CSV (never changes MySQL).
--preview validates explicitly approved CSV entries (never changes MySQL).
--apply --confirm-reviewed --place-ids ... updates only named Kabankalan Places.

Local files must be supplied and independently inspected with photographer/owner
permission. This command cannot verify the truth of human-supplied rights evidence.
"""
import csv
import hashlib
import html
import os
import re
import shutil
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from PIL import Image, UnidentifiedImageError

from apps.cities.models import City
from apps.places.models import Place

CITY_ID = 2
REVIEW = Path(settings.BASE_DIR) / 'phase6_photo_review'
STAGING = REVIEW / 'kabankalan_local_uploads'
CSV_PATH = REVIEW / 'kabankalan_local_photo_review.csv'
GALLERY = REVIEW / 'kabankalan_local_photo_review.html'
DESTINATION_DIR = 'places/covers/kabankalan_reviewed'
MAX_FILE_BYTES = 15 * 1024 * 1024
MAX_IMAGE_PIXELS = 30_000_000
MAX_IMPORT = 20
FORMATS = {'.jpg': 'JPEG', '.jpeg': 'JPEG', '.png': 'PNG', '.webp': 'WEBP'}
LICENSE_PATHS = {
    'CC BY 4.0': '/licenses/by/4.0',
    'CC BY 3.0': '/licenses/by/3.0',
    'CC BY-SA 4.0': '/licenses/by-sa/4.0',
    'CC BY-SA 3.0': '/licenses/by-sa/3.0',
    'CC0 1.0': '/publicdomain/zero/1.0',
}
FIELDS = (
    'place_id', 'place_slug', 'place_name', 'city_id', 'already_has_cover',
    'file_name', 'file_sha256', 'photo_credit', 'photo_source_url',
    'photo_license', 'photo_license_url', 'identity_evidence',
    'rights_evidence', 'review_decision', 'identity_checked',
    'rights_checked', 'review_notes',
)
UNTRUSTED_EDIT_FIELDS = set(FIELDS) - {
    'place_id', 'place_slug', 'place_name', 'city_id', 'already_has_cover'
}


def safe_name(name):
    """Only a single regular filename, never a path, link or traversal."""
    if not isinstance(name, str) or not name or len(name) > 160:
        return False
    if name != Path(name).name or '/' in name or '\\' in name or ':' in name:
        return False
    if not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9._ -]*', name):
        return False
    return Path(name).suffix.lower() in FORMATS and name not in ('.', '..')


def trusted_url(value, hosts):
    if not value:
        return False
    try:
        uri = urlsplit(str(value).strip())
        return (uri.scheme == 'https' and uri.hostname in hosts
                and uri.username is None and uri.password is None
                and uri.port in (None, 443) and not uri.fragment)
    except (ValueError, TypeError):
        return False


def read_rows():
    if not CSV_PATH.exists():
        raise CommandError('Review CSV missing. Run --inventory first.')
    with CSV_PATH.open('r', newline='', encoding='utf-8-sig') as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or set(reader.fieldnames) != set(FIELDS):
            raise CommandError('CSV headings changed. Original preserved; investigate manually.')
        rows = list(reader)
    seen = set()
    for row in rows:
        identifier = row['place_id']
        if not identifier.isascii() or not identifier.isdecimal() or identifier in seen:
            raise CommandError('Duplicate/malformed place IDs in review CSV. Nothing changed.')
        seen.add(identifier)
        if row['city_id'] != str(CITY_ID):
            raise CommandError('Non-Kabankalan row in local review CSV. Nothing changed.')
    return rows


def write_rows(rows):
    REVIEW.mkdir(parents=True, exist_ok=True)
    tmp = CSV_PATH.with_name(CSV_PATH.name + '.tmp')
    with tmp.open('w', newline='', encoding='utf-8-sig') as fh:
        writer = csv.DictWriter(fh, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    os.replace(tmp, CSV_PATH)


def verified_file(row):
    name = (row.get('file_name') or '').strip()
    if not safe_name(name):
        raise ValueError('Invalid file_name: use one .jpg/.jpeg/.png/.webp filename, no paths')
    path = STAGING / name
    if path.is_symlink() or not path.is_file():
        raise ValueError('Staged file missing or symlink refused')
    if path.stat().st_size < 100 or path.stat().st_size > MAX_FILE_BYTES:
        raise ValueError('File size outside 100 bytes–15 MB')
    try:
        with Image.open(path) as img:
            if img.format != FORMATS[Path(name).suffix.lower()]:
                raise ValueError('File extension does not match actual image format')
            if img.width * img.height > MAX_IMAGE_PIXELS:
                raise ValueError('Image exceeds 30 megapixels')
            img.verify()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError('Invalid/unsafe image: ' + str(exc)) from exc
    digest = hashlib.sha256()
    with path.open('rb') as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b''):
            digest.update(chunk)
    expected = (row.get('file_sha256') or '').strip().lower()
    if not re.fullmatch(r'[a-f0-9]{64}', expected) or digest.hexdigest() != expected:
        raise ValueError('Image SHA256 missing or different: re-review actual file bytes')
    return path, digest.hexdigest()


def review_errors(row, place):
    problems = []
    if place is None or place.city_id != CITY_ID:
        return ['Place missing or not Kabankalan'], None, None
    if str(place.pk) != row['place_id'] or place.slug != row['place_slug'] or place.title != row['place_name']:
        problems.append('Place identifier/name/slug changed')
    if place.cover_image or place.cover_image_url:
        problems.append('Existing cover cannot be overwritten')
    if (row.get('review_decision') or '').strip().lower() != 'approve':
        problems.append('Not approved')
    if (row.get('identity_checked') or '').strip().lower() != 'yes':
        problems.append('Identity not independently checked')
    if (row.get('rights_checked') or '').strip().lower() != 'yes':
        problems.append('Rights not independently checked')
    for key in ('identity_evidence', 'rights_evidence', 'review_notes'):
        if len((row.get(key) or '').strip()) < 20:
            problems.append(key + ' needs meaningful evidence (20+ characters)')
    credit = (row.get('photo_credit') or '').strip()
    if not credit or len(credit) > Place._meta.get_field('photo_credit').max_length:
        problems.append('Missing/too-long photographer credit')
    license_name = (row.get('photo_license') or '').strip()
    license_url = (row.get('photo_license_url') or '').strip()
    source_url = (row.get('photo_source_url') or '').strip()
    if license_name == 'Used with permission':
        if license_url:
            problems.append('Owner permission is not a Creative Commons license; leave license URL empty')
    elif license_name in LICENSE_PATHS:
        if not trusted_url(license_url, {'creativecommons.org'}):
            problems.append('Untrusted CC license URL')
        elif urlsplit(license_url).path.rstrip('/') != LICENSE_PATHS[license_name]:
            problems.append('License link does not match declared CC license')
        if not source_url:
            problems.append('CC images require a traceable original photo source URL')
    else:
        problems.append('License must be a supported CC type or Used with permission')
    if source_url and not trusted_url(source_url, {'commons.wikimedia.org', 'www.wikimedia.org', 'www.wikipedia.org'}):
        # Owner/creator URLs may be on their own website, not just Wikimedia.
        try:
            parsed = urlsplit(source_url)
            if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
                problems.append('Invalid HTTPS source URL')
        except ValueError:
            problems.append('Invalid source URL')
    for model_field, value in (('photo_source_url', source_url), ('photo_license_url', license_url),
                               ('photo_license', license_name)):
        if len(value) > Place._meta.get_field(model_field).max_length:
            problems.append(model_field + ' exceeds model length')
    try:
        path, digest = verified_file(row)
    except ValueError as exc:
        problems.append(str(exc))
        path = None
        digest = None
    return problems, path, digest


def write_gallery(rows):
    STAGING.mkdir(parents=True, exist_ok=True)
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>Kabankalan local photo review</title>',
             '<style>body{font:15px system-ui;margin:30px auto;max-width:1250px;padding:0 18px}',
             '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:14px}',
             'article{border:1px solid #ddd;padding:12px;border-radius:12px}',
             'img{max-width:100%;width:100%;height:190px;object-fit:cover}</style>',
             '<h1>Kabankalan staged local-photo review</h1>',
             '<p>Preview only. Inspect each original image and written identity/rights evidence. '
             'This report does not approve any photos.</p><div class="grid">']
    count = 0
    for row in rows:
        name = (row.get('file_name') or '').strip()
        if not safe_name(name) or not (STAGING / name).is_file() or (STAGING / name).is_symlink():
            continue
        esc = lambda val: html.escape(str(val or ''), quote=True)
        parts.append('<article><img src="kabankalan_local_uploads/' + esc(name) + '" alt="Unverified photo"><h3>'
                     + esc(row['place_name']) + '</h3><p>ID ' + esc(row['place_id'])
                     + ' — ' + esc(row.get('review_decision') or 'not reviewed')
                     + '</p><p>Creator: ' + esc(row.get('photo_credit'))
                     + '</p><p>License/permission: ' + esc(row.get('photo_license')) + '</p></article>')
        count += 1
    parts.append('</div><p>' + str(count) + ' staged previews.</p></html>')
    GALLERY.write_text(''.join(parts), encoding='utf-8')
    return count


class Command(BaseCommand):
    help = 'Kabankalan-only local cover-photo inventory, independent review, guarded targeted import.'

    def add_arguments(self, parser):
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('--inventory', action='store_true', help='Create/refresh local upload review CSV; no DB writes')
        group.add_argument('--preview', action='store_true', help='Validate approved staged photos; no DB writes')
        group.add_argument('--apply', action='store_true', help='Import selected independently approved staged photos')
        parser.add_argument('--confirm-reviewed', action='store_true', help='Required with --apply')
        parser.add_argument('--place-ids', help='Comma-separated exact Kabankalan Place IDs (required with --apply)')

    def handle(self, *args, **opts):
        city = City.objects.filter(pk=CITY_ID).first()
        if not city or city.name.strip().casefold() != 'kabankalan':
            raise CommandError('City ID 2 is not Kabankalan. No action taken.')
        if opts['confirm_reviewed'] and not opts['apply']:
            raise CommandError('--confirm-reviewed only valid with --apply')
        if opts['apply'] and (not opts['confirm_reviewed'] or not opts.get('place_ids')):
            raise CommandError('Apply requires BOTH --confirm-reviewed and --place-ids')
        ids = None
        if opts.get('place_ids'):
            raw = opts['place_ids'].split(',')
            if (not raw or any(not token.strip().isascii() or not token.strip().isdecimal() for token in raw)
                    or len(raw) != len(set(raw)) or len(raw) > MAX_IMPORT):
                raise CommandError('Provide 1–20 distinct numeric Place IDs')
            ids = {int(item.strip()) for item in raw}
        if opts['inventory']:
            places = list(Place.objects.filter(city_id=CITY_ID).order_by('pk'))
            old = read_rows() if CSV_PATH.exists() else []
            prev = {r['place_id']: r for r in old}
            new = []
            for place in places:
                row = {
                    'place_id': str(place.pk), 'place_slug': place.slug,
                    'place_name': place.title, 'city_id': str(CITY_ID),
                    'already_has_cover': 'yes' if place.cover_image or place.cover_image_url else 'no',
                    **{key: '' for key in UNTRUSTED_EDIT_FIELDS},
                }
                prior = prev.get(row['place_id'])
                if prior:
                    if prior['place_slug'] != place.slug or prior['place_name'] != place.title:
                        raise CommandError(f'Place {place.pk} changed. CSV untouched; review manually.')
                    row.update({key: prior.get(key, '') for key in UNTRUSTED_EDIT_FIELDS})
                new.append(row)
            if old:
                import datetime
                backup = CSV_PATH.with_name(CSV_PATH.name + '.backup-' + datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
                shutil.copy2(CSV_PATH, backup)
                self.stdout.write('Existing review CSV backed up: ' + str(backup))
            write_rows(new)
            count = write_gallery(new)
            self.stdout.write(self.style.SUCCESS(f'INVENTORY READY: {len(new)} Kabankalan places, '
                                                 f'{sum(r["already_has_cover"] == "no" for r in new)} missing covers, '
                                                 f'{count} local file previews. DATABASE UNCHANGED.'))
            self.stdout.write(f'CSV: {CSV_PATH}\nLOCAL UPLOAD FOLDER: {STAGING}\nGALLERY: {GALLERY}')
            return
        rows = read_rows()
        approved = [r for r in rows if (r.get('review_decision') or '').strip().lower() == 'approve'
                    and (ids is None or int(r['place_id']) in ids)]
        if opts['apply'] and {int(r['place_id']) for r in approved} != ids:
            raise CommandError('Every specified Place ID must have exactly one approved CSV row. Nothing changed.')
        if opts['apply'] and len(approved) > MAX_IMPORT:
            raise CommandError(f'At most {MAX_IMPORT} approvals per import. Use --place-ids to select a batch.')
        places = Place.objects.filter(city_id=CITY_ID, pk__in=[r['place_id'] for r in approved]).in_bulk()
        results = []
        duplicates = {}
        for row in approved:
            issues, path, digest = review_errors(row, places.get(int(row['place_id'])))
            if digest:
                duplicates.setdefault(digest, []).append(row['place_id'])
            results.append((row, issues, path, digest))
        for row, issues, path, digest in results:
            if digest and len(duplicates[digest]) > 1:
                issues.append('Same staged image is approved for multiple places')
        invalid = [(r, e) for r, e, _, _ in results if e]
        self.stdout.write(f'LOCAL PHOTO REVIEW: {len(approved)} approved, {len(results)-len(invalid)} eligible, {len(invalid)} blocked.')
        for row, errs, _, _ in results[:30]:
            if errs:
                self.stdout.write(f'  BLOCKED {row["place_id"]} {row["place_name"]}: ' + '; '.join(errs))
            else:
                self.stdout.write(f'  READY {row["place_id"]}: {row["place_name"]}')
        if opts['preview']:
            self.stdout.write('PREVIEW ONLY. Database and uploaded covers unchanged.')
            return
        if invalid:
            raise CommandError('Import refused: at least one selected approval failed validation. Nothing changed.')
        if not results:
            raise CommandError('No approved records selected for import.')
        media_root = Path(settings.MEDIA_ROOT).resolve()
        output_dir = media_root / DESTINATION_DIR
        new_paths = []
        try:
            with transaction.atomic():
                locked = {p.pk: p for p in Place.objects.select_for_update().filter(
                    city_id=CITY_ID, pk__in=[int(row['place_id']) for row, _, _, _ in results]
                )}
                for row, _, file_path, digest in results:
                    errors, verified_path, verified_digest = review_errors(row, locked.get(int(row['place_id'])))
                    if errors or verified_digest != digest:
                        raise CommandError('Place/photo changed since preview for ID ' + row['place_id'] + ': ' + '; '.join(errors))
                    filename = f'{row["place_id"]}_{digest[:16]}{file_path.suffix.lower()}'
                    destination = output_dir / filename
                    output_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        with destination.open('xb') as outgoing, verified_path.open('rb') as incoming:
                            new_paths.append(destination)
                            shutil.copyfileobj(incoming, outgoing)
                    except FileExistsError as exc:
                        raise CommandError('Media file already exists: refusing to overwrite ' + filename) from exc
                    written_hash = hashlib.sha256()
                    with destination.open('rb') as check_file:
                        for part in iter(lambda: check_file.read(1024 * 1024), b''):
                            written_hash.update(part)
                    if written_hash.hexdigest() != digest:
                        raise CommandError('Staged photo changed while being copied: ' + row['place_id'])
                    rel_name = f'{DESTINATION_DIR}/{filename}'
                    updated = Place.objects.filter(pk=int(row['place_id']), city_id=CITY_ID, slug=row['place_slug']).filter(
                        Q(cover_image='') | Q(cover_image__isnull=True)
                    ).filter(Q(cover_image_url='') | Q(cover_image_url__isnull=True)).update(
                        cover_image=rel_name,
                        photo_credit=row['photo_credit'].strip(),
                        photo_source_url=row['photo_source_url'].strip(),
                        photo_license=row['photo_license'].strip(),
                        photo_license_url=row['photo_license_url'].strip(),
                    )
                    if updated != 1:
                        raise CommandError('Place changed during import; database rolled back for ID ' + row['place_id'])
        except Exception:
            for filename in new_paths:
                try:
                    filename.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        self.stdout.write(self.style.SUCCESS(f'IMPORTED {len(results)} reviewed Kabankalan local cover(s). '
                                             'No other-city/verification/publication fields changed.'))
