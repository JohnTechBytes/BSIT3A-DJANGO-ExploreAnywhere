"""Import the normalized PSA PSGC Q3 2026 CSV without changing existing city PKs.

Usage: python manage.py load_psgc data/psgc_2026_q3_exploreanywhere.csv
"""
import csv
import re
import unicodedata
from collections import Counter
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from apps.cities.models import City, Province


def canonical(name):
    value = unicodedata.normalize('NFKC', name or '').strip().casefold()
    value = re.sub(r'^city of\s+', '', value)
    value = re.sub(r'\s+city$', '', value)
    value = re.sub(r'\s+', ' ', value)
    return value


def compact_slug(name, code, max_length):
    base = slugify(name) or 'area'
    suffix = '-' + code.lower()
    return base[:max_length - len(suffix)] + suffix


class Command(BaseCommand):
    help = 'Import normalized PSA PSGC provinces and cities/municipalities, preserving existing IDs.'

    def add_arguments(self, parser):
        parser.add_argument('file')

    def handle(self, *args, **options):
        source = Path(options['file'])
        if not source.is_file():
            raise CommandError(f'File not found: {source}')
        with source.open('r', encoding='utf-8-sig', newline='') as f:
            reader = csv.DictReader(f)
            required = {'psgc_code','name','level','region_code','region_name','province_code'}
            if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
                raise CommandError(f'CSV requires columns: {sorted(required)}')
            rows = [{k: (v or '').strip() for k, v in r.items()} for r in reader]
        codes = [row['psgc_code'] for row in rows]
        if not rows or any(not code for code in codes) or len(codes) != len(set(codes)):
            raise CommandError('CSV is empty, has empty codes, or duplicates PSGC codes.')
        if any(len(code) > 20 for code in codes):
            raise CommandError('A PSGC code exceeds the 20-character model limit.')

        province_rows = [r for r in rows if r['level'] in ('province', 'province_group')]
        locality_rows = [r for r in rows if r['level'] in ('city', 'municipality')]
        parent_codes = {r['psgc_code'] for r in province_rows}
        missing = [r['name'] for r in locality_rows if r['province_code'] not in parent_codes]
        if missing:
            raise CommandError(f'Unresolved parent for: {missing[:5]}')

        stats = Counter()
        with transaction.atomic():
            # 1. Create official provinces and clearly labelled region-level groups.
            for r in province_rows:
                code, name = r['psgc_code'], r['name']
                obj = Province.objects.filter(psgc_code=code).first()
                if obj is None and r['level'] == 'province':
                    legacy = list(Province.objects.filter(name__iexact=name))
                    legacy = [p for p in legacy if p.psgc_code.startswith(('TMP-', 'LOCAL-'))]
                    if len(legacy) == 1:
                        obj = legacy[0]
                        stats['legacy_provinces_reused'] += 1
                if obj is None:
                    obj = Province(psgc_code=code)
                    stats['provinces_created'] += 1
                obj.name = name
                obj.slug = compact_slug(name, code, 180)
                obj.region = r['region_name']
                obj.region_code = r['region_code']
                obj.psgc_code = code
                obj.save()

            parents = Province.objects.in_bulk(field_name='psgc_code')
            region_official_provinces = {}
            for r in province_rows:
                if r['level'] == 'province':
                    region_official_provinces.setdefault(r['region_code'], set()).add(r['name'].casefold())

            # Keep reference to ORIGINAL seed province string for accurate matching.
            # A city such as Bacolod also exists as a municipality in another province.
            legacy = list(City.objects.filter(psgc_code__isnull=True))
            unassigned = {c.pk: c for c in legacy}

            for r in locality_rows:
                code = r['psgc_code']
                parent = parents[r['province_code']]
                obj = City.objects.filter(psgc_code=code).first()
                if obj is None:
                    matches = []
                    for c in unassigned.values():
                        if canonical(c.name) != canonical(r['name']):
                            continue
                        # Ordinary municipalities: require the same real province.
                        if r['province_code'].startswith('GRP-'):
                            # Independent city: reuse existing seed only when the
                            # seed province belongs to the same official region.
                            if c.province.casefold() not in region_official_provinces.get(r['region_code'], set()):
                                continue
                        elif c.province.casefold() != parent.name.casefold():
                            continue
                        matches.append(c)
                    if len(matches) == 1:
                        obj = matches[0]
                        del unassigned[obj.pk]
                        stats['legacy_cities_reused'] += 1
                if obj is None:
                    # Newly imported places are Pending until curated/reviewed.
                    obj = City(
                        name=r['name'],
                        slug=compact_slug(r['name'], code, 200),
                        status='pending',
                        country='Philippines',
                        province=parent.name,
                        latitude=None,
                        longitude=None,
                    )
                    stats['cities_created'] += 1
                # Preserve legacy city name/slug/coordinates/status when reused.
                obj.psgc_code = code
                obj.kind = r['kind'] or r['level']
                obj.province_ref = parent
                obj.save()

            # Link any remaining legacy records to official provinces by name.
            for obj in unassigned.values():
                candidates = [p for p in parents.values() if p.name.casefold() == obj.province.casefold() and not p.psgc_code.startswith('GRP-')]
                if len(candidates) == 1 and obj.province_ref_id != candidates[0].pk:
                    obj.province_ref = candidates[0]
                    obj.save(update_fields=['province_ref'])
                    stats['unmatched_legacy_linked'] += 1

            # Remove unused temporary province placeholders, never delete real rows.
            for p in Province.objects.all():
                if p.psgc_code.startswith(('TMP-', 'LOCAL-')) and not p.cities.exists():
                    p.delete()
                    stats['obsolete_local_groups_removed'] += 1

        self.stdout.write(self.style.SUCCESS(
            'PSGC import committed: ' + ', '.join(f'{k}={v}' for k,v in sorted(stats.items()))
        ))
        self.stdout.write(
            f'Province/group records: {Province.objects.count()}; Cities/municipalities: {City.objects.count()}; '
            f'Existing city IDs preserved when unambiguously matched.'
        )
