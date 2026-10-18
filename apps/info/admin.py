
from django.contrib import admin

from .models import (
    CityInformation,
    SusResponse,
    RecommendationRating,
    QueryLog,
)


@admin.register(CityInformation)
class CityInformationAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "city",
        "info_type",
        "order",
        "created_at",
    )
    list_filter = ("city", "info_type")
    search_fields = ("title", "description", "city__name")
    ordering = ("city", "info_type", "order")


@admin.register(SusResponse)
class SusResponseAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "score", "created_at")
    list_filter = ("created_at",)
    readonly_fields = ("score", "created_at")


@admin.register(RecommendationRating)
class RecommendationRatingAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "place",
        "user",
        "rating",
        "created_at",
    )
    list_filter = ("rating", "created_at")
    search_fields = ("place__name", "query_text")


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "matched_count",
        "created_at",
    )
    search_fields = ("raw_query",)
    readonly_fields = ("created_at",)
