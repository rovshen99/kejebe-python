from django.contrib import admin

from .models import SystemContact


@admin.register(SystemContact)
class SystemContactAdmin(admin.ModelAdmin):
    list_display = ("type", "value", "is_active", "priority", "created_at")
    list_filter = ("is_active", "type")
    search_fields = ("value", "type__slug", "type__name_tm", "type__name_ru")
    ordering = ("priority", "id")
