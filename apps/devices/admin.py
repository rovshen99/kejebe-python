from django.contrib import admin

from apps.devices.models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_id", "platform", "user", "city", "region", "last_seen_at", "created_at")
    list_filter = ("platform", "city", "region")
    search_fields = ("device_id", "user__name", "user__surname", "user__email")
    readonly_fields = ("created_at", "updated_at", "last_seen_at")
