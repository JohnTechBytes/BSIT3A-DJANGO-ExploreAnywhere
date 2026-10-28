
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.text import slugify

from apps.cities.models import City, Province


class Command(BaseCommand):
    help = "Link existing cities to temporary local province records."

    @transaction.atomic
    def handle(self, *args, **options):
        province_names = (
            City.objects.exclude(province="")
            .values_list("province", flat=True)
            .distinct()
        )

        linked = 0

        for name in province_names:
            name = name.strip()
            if not name:
                continue

            # Reuse a matching existing province if present.
            matches = Province.objects.filter(name__iexact=name)

            if matches.count() == 1:
                province = matches.first()
            elif matches.count() > 1:
                self.stdout.write(
                    self.style.WARNING(
                        f"Ambiguous province: {name}. Skipping."
                    )
                )
                continue
            else:
                local_code = "TMP-" + __import__("hashlib").sha256(
                    name.casefold().encode("utf-8")
                ).hexdigest()[:12]

                province, _ = Province.objects.get_or_create(
                    psgc_code=local_code,
                    defaults={
                        "name": name,
                        "slug": f"local-{slugify(name)}",
                        "region": "Local data - pending PSGC",
                        "region_code": "LOCAL",
                    },
                )

            updated = City.objects.filter(
                province__iexact=name
            ).exclude(
                province_ref=province
            ).update(province_ref=province)

            linked += updated

            self.stdout.write(
                f"{province.name}: "
                f"{City.objects.filter(province_ref=province).count()} cities"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Complete. Provinces: {Province.objects.count()}; "
                f"cities newly linked: {linked}"
            )
        )
