import nested_admin
from django.contrib import admin
from django.contrib.contenttypes.models import ContentType

from apps.banners.models import Banner
from apps.categories.models import Category
from apps.services.models import Service
from .models import HomePageConfig, HomeBlock, HomeBlockItem


class HomeBlockItemInline(nested_admin.NestedTabularInline):
    model = HomeBlockItem
    extra = 0
    sortable_field_name = "position"
    fields = ("content_type", "object_id", "position")

    def get_formset(self, request, obj=None, **kwargs):
        formset = super().get_formset(request, obj, **kwargs)
        qs = ContentType.objects.get_for_models(Service, Banner, Category)
        allowed_ids = [ct.id for ct in qs.values()]
        formset.form.base_fields["content_type"].queryset = ContentType.objects.filter(id__in=allowed_ids)
        return formset


class HomeBlockInline(nested_admin.NestedStackedInline):
    model = HomeBlock
    extra = 0
    sortable_field_name = "position"
    inlines = [HomeBlockItemInline]
    fieldsets = (
        (None, {
            "fields": (
                "type",
                ("title_tm", "title_ru", "title_en"),
                "position",
                "is_active",
                "source_mode",
                "limit",
            )
        }),
        ("Data & style", {
            "classes": ("collapse",),
            "fields": ("query_params", "style"),
        }),
    )


@admin.register(HomePageConfig)
class HomePageConfigAdmin(nested_admin.NestedModelAdmin):
    list_display = ("slug", "city", "region", "locale", "is_active", "priority")
    list_filter = ("locale", "is_active", "city", "region")
    search_fields = ("slug", "title")
    ordering = ("-priority", "id")
    inlines = [HomeBlockInline]


@admin.register(HomeBlock)
class HomeBlockAdmin(admin.ModelAdmin):
    list_display = ("id", "config", "type", "position", "is_active", "source_mode", "limit")
    list_filter = ("type", "source_mode", "is_active", "config__city", "config__region", "config__locale")
    search_fields = ("config__slug", "title_tm", "title_ru", "title_en")
    ordering = ("config", "position", "id")


@admin.register(HomeBlockItem)
class HomeBlockItemAdmin(admin.ModelAdmin):
    list_display = ("block", "content_object", "position")
    search_fields = ("block__config__slug",)
    ordering = ("block", "position", "id")
