from django.contrib import admin

from apps.stories.models import ServiceStory, ServiceStoryView


@admin.register(ServiceStory)
class ServiceStoryAdmin(admin.ModelAdmin):
    list_display = ("id", "service", "title", "is_active", "starts_at", "ends_at", "priority", "created_at")
    list_filter = ("is_active", "starts_at", "ends_at", "priority")
    search_fields = ("title", "service__title_tm", "service__title_ru", "service__title_en")
    readonly_fields = ("created_at", "updated_at")


@admin.register(ServiceStoryView)
class ServiceStoryViewAdmin(admin.ModelAdmin):
    list_display = ("story", "user", "device", "viewed_at")
    list_filter = ("story", "user")
    search_fields = ("story__title", "user__name", "user__surname", "device__device_id")
    readonly_fields = ("viewed_at",)
