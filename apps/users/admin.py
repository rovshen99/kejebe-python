from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserPhoneHistory


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User
    list_display = ("phone", "name", "email", "role", "is_staff", "is_active", "created_at")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("phone", "name", "email")
    ordering = ("-created_at",)
    readonly_fields = ("created_at", "updated_at", "last_login", "deleted_at")

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal info", {"fields": ("name", "surname", "email", "role", "city", "avatar")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at", "deleted_at")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "password1", "password2", "name", "surname", "email", "role", "city", "avatar", "is_staff", "is_active"),
        }),
    )

    def get_readonly_fields(self, request, obj=None):
        return self.readonly_fields + (() if obj is None else ("created_at", "updated_at"))


@admin.register(UserPhoneHistory)
class UserPhoneHistoryAdmin(admin.ModelAdmin):
    list_display = ("phone", "user", "assigned_at", "revoked_at")
    search_fields = ("phone", "user__phone", "user__name", "user__email")
    list_filter = ("revoked_at",)
    ordering = ("-revoked_at",)
