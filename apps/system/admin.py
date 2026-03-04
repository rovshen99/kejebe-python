from django.contrib import admin
from django_summernote.admin import SummernoteModelAdmin

from .models import SystemContact, AccountDeletionRequest, SystemAbout


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


@admin.register(SystemAbout)
class SystemAboutAdmin(SummernoteModelAdmin):
    list_display = ("id", "updated_at")
    ordering = ("-updated_at", "-id")
    summernote_fields = ("about_tm", "about_ru")

    def has_add_permission(self, request):
        return not SystemAbout.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

