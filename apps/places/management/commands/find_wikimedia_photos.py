import ssl
import certifi
import csv
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from django.core.management.base import BaseCommand, CommandError

from apps.places.models import Place


CSV_PATH = Path(
    "data/osm/extracted/philippines_attractions_nodes.csv"
)

REPORT_PATH = Path(
    "data/osm/validation/wikimedia_photo_candidates.csv"
)


def fetch_json(url):
    user_agent = os.getenv("WIKIMEDIA_USER_AGENT")

    if not user_agent:
        raise ValueError(
            "Set WIKIMEDIA_USER_AGENT with an "
            "application name and contact address."
        )

    request = Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept": "application/json",
        },
    )

    context = ssl.create_default_context(
        cafile=certifi.where()
    )

    with urlopen(
        request,
        timeout=25,
        context=context,
    ) as response:
        return json.load(response)


def get_wikidata_image(qid):
    if not re.fullmatch(r"Q[1-9][0-9]*", qid):
        return None

    url = (
        "https://www.wikidata.org/wiki/Special:EntityData/"
        + quote(qid)
        + ".json"
    )

    data = fetch_json(url)

    entity = data.get("entities", {}).get(qid, {})
    claims = entity.get("claims", {}).get("P18", [])

    for claim in claims:
        filename = (
            claim.get("mainsnak", {})
            .get("datavalue", {})
            .get("value")
        )

        if isinstance(filename, str) and filename.strip():
            return filename.strip()

    return None


def get_commons_metadata(filename):
    params = {
        "action": "query",
        "format": "json",
        "titles": "File:" + filename,
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
    }

    url = (
        "https://commons.wikimedia.org/w/api.php?"
        + urlencode(params)
    )

    data = fetch_json(url)

    pages = data.get("query", {}).get("pages", {})

    for page in pages.values():
        image_info = page.get("imageinfo", [])

        if not image_info:
            continue

        info = image_info[0]
        metadata = info.get("extmetadata", {})

        def value(name):
            return metadata.get(name, {}).get("value", "")

        return {
            "image_url": (
                info.get("thumburl")
                or info.get("url")
                or ""
            ),
            "source_url": (
                info.get("descriptionurl")
                or ""
            ),
            "license": value("LicenseShortName"),
            "artist": value("Artist"),
"attribution": value("Attribution"),
"credit": value("Credit"),
            "license_url": value("LicenseUrl"),
            "attribution_required": value(
                "AttributionRequired"
            ),
        }

    return None


class Command(BaseCommand):
    help = (
        "Preview real Wikimedia photo candidates "
        "matched by imported OSM and Wikidata IDs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Maximum Wikidata-linked attractions to inspect.",
        )

    def handle(self, *args, **options):
        limit = options["limit"]

        if limit < 1 or limit > 100:
            raise CommandError(
                "--limit must be between 1 and 100."
            )

        if not CSV_PATH.exists():
            raise CommandError(
                f"Missing OSM CSV: {CSV_PATH}"
            )

        if not os.getenv("WIKIMEDIA_USER_AGENT"):
            raise CommandError(
                "Set WIKIMEDIA_USER_AGENT before running."
            )

        # Match only records actually present in MySQL.
        imported_ids = set(
            Place.objects.filter(
                slug__startswith="osm-"
            ).values_list("slug", flat=True)
        )

        matched = []
        total_wikidata = 0

        with CSV_PATH.open(
            encoding="utf-8-sig",
            newline=""
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    tags = json.loads(
                        row.get("tags_json") or "{}"
                    )
                except (ValueError, TypeError):
                    continue

                if not isinstance(tags, dict):
                    continue

                qid = str(
                    tags.get("wikidata") or ""
                ).strip()

                if not re.fullmatch(r"Q[1-9][0-9]*", qid):
                    continue

                total_wikidata += 1

                if row["osm_id"] not in imported_ids:
                    continue

                matched.append({
                    "osm_id": row["osm_id"],
                    "name": row["name"],
                    "wikidata": qid,
                })

        self.stdout.write(
            f"OSM nodes with Wikidata: {total_wikidata}"
        )
        self.stdout.write(
            f"Imported places with Wikidata: {len(matched)}"
        )

        matched = matched[:limit]
        results = []

        for index, item in enumerate(matched, start=1):
            name = item["name"]
            qid = item["wikidata"]

            self.stdout.write(
                f"[{index}/{len(matched)}] {name} ({qid})"
            )

            try:
                filename = get_wikidata_image(qid)

                if not filename:
                    self.stdout.write(
                        "  No Wikidata P18 image."
                    )
                    continue

                metadata = get_commons_metadata(filename)

                if not metadata or not metadata["image_url"]:
                    self.stdout.write(
                        "  Commons image metadata unavailable."
                    )
                    continue

                results.append({
                    **item,
                    "filename": filename,
                    **metadata,
                })

                self.stdout.write(
                    "  Photo candidate found."
                )
                self.stdout.write(
                    f"  License: {metadata['license']}"
                )
                self.stdout.write(
                    f"  Source: {metadata['source_url']}"
                )

            except (
                HTTPError,
                URLError,
                TimeoutError,
                ValueError,
                OSError,
            ) as error:
                self.stderr.write(
                    f"  API request failed: {error}"
                )

            # Keep request frequency conservative.
            time.sleep(0.5)

        REPORT_PATH.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        fields = [
            "artist",
"attribution",
"credit",
            "osm_id",
            "name",
            "wikidata",
            "filename",
            "image_url",
            "source_url",
            "license",
            "license_url",
            "attribution_required",
        ]

        with REPORT_PATH.open(
            "w",
            encoding="utf-8",
            newline=""
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fields
            )
            writer.writeheader()
            writer.writerows(results)

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Found {len(results)} photo candidates."
            )
        )
        self.stdout.write(
            f"Report saved: {REPORT_PATH}"
        )
        self.stdout.write(
            "PREVIEW ONLY. MySQL was not modified."
        )
