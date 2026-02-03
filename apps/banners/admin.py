from django.contrib import admin
from django.db import models
from django_json_widget.widgets import JSONEditorWidget
from .models import Banner


@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ("id", "title_tm", "is_active", "starts_at", "ends_at", "open_type", "priority")
    list_filter = ("is_active", "regions", "cities")
    search_fields = ("title_tm", "title_ru")
    filter_horizontal = ("regions", "cities")
    ordering = ("priority", "-created_at")
    formfield_overrides = {
        models.JSONField: {"widget": JSONEditorWidget},
    }
