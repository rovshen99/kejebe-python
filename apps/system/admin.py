from django.contrib import admin

from .models import SystemContact, AccountDeletionRequest


@admin.register(SystemContact)
class SystemContactAdmin(admin.ModelAdmin):
    list_display = ("type", "value", "is_active", "priority", "created_at")
    list_filter = ("is_active", "type")
    search_fields = ("value", "type__slug", "type__name_tm", "type__name_ru")
    ordering = ("priority", "id")


@admin.register(AccountDeletionRequest)
class AccountDeletionRequestAdmin(admin.ModelAdmin):
    list_display = ("phone", "status", "created_at")
    list_filter = ("status",)
    search_fields = ("phone",)
    ordering = ("-created_at",)
