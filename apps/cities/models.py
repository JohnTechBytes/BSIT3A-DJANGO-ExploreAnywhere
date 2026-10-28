from django.db import models


class Province(models.Model):
    name = models.CharField(max_length=160)

    slug = models.SlugField(
        max_length=180,
        unique=True
    )

    region = models.CharField(max_length=160)

    region_code = models.CharField(
        max_length=20,
        db_index=True
    )

    psgc_code = models.CharField(
        max_length=20,
        unique=True
    )

    class Meta:
        ordering = ["region", "name"]
        indexes = [
            models.Index(fields=["region"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.region}"


class City(models.Model):

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PENDING = "pending", "Pending"

    class Kind(models.TextChoices):
        CITY = "city", "City"
        MUNICIPALITY = "municipality", "Municipality"

    # ORIGINAL FIELDS FROM 0001_initial.py

    name = models.CharField(max_length=200)

    slug = models.SlugField(
        max_length=200,
        unique=True
    )

    province = models.CharField(
        max_length=200,
        default="Negros Occidental"
    )

    country = models.CharField(
        max_length=100,
        default="Philippines"
    )

    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True
    )

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    banner_image = models.ImageField(
        upload_to="cities/banners/",
        blank=True,
        null=True
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
    )

    # NEW PSGC FIELDS - ADDITIVE MIGRATION

    province_ref = models.ForeignKey(
        Province,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="cities"
    )

    psgc_code = models.CharField(
        max_length=20,
        unique=True,
        null=True,
        blank=True
    )

    kind = models.CharField(
        max_length=20,
        choices=Kind.choices,
        default=Kind.CITY
    )

    class Meta:
        db_table = "explore_cities"
        verbose_name_plural = "Cities"
        ordering = ["name"]

        indexes = [
            models.Index(
                fields=["province_ref", "status"],
                name="city_prov_status_idx"
            ),
        ]

    def __str__(self):
        return f"{self.name}, {self.province}"
