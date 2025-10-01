from django.contrib import admin
from .models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("id", "title_tm", "is_active", "starts_at", "ends_at", "priority")
    list_filter = ("is_active", "regions", "cities")
    search_fields = ("title_tm", "title_ru", "title_en")
    filter_horizontal = ("regions", "cities")
    ordering = ("priority", "-created_at")

