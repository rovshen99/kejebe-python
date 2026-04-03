import nested_admin
from django import forms
from django.conf import settings
from django.contrib import admin

from core.mixins import IconPreviewMixin
from .models import (
    Service,
    ServiceContact,
    ServiceImage,
    ServiceVideo,
    Review,
    Favorite,
    ServiceTag,
    Attribute,
    AttributeValue,
    ContactType,
    ServiceProductImage,
    ServiceProduct,
    ServiceApplication,
    ServiceApplicationImage,
    ServiceApplicationLink,
)


class ServiceContactInline(nested_admin.NestedTabularInline):
    model = ServiceContact
    extra = 1


class ServiceImageInline(nested_admin.NestedTabularInline):
    model = ServiceImage
    extra = 1


class ServiceVideoInline(IconPreviewMixin, nested_admin.NestedTabularInline):
    model = ServiceVideo
    extra = 1
    icon_field_name = "preview"
    icon_width = 80
    icon_height = 80
    readonly_fields = ("icon_preview", "hls_ready", "hls_playlist")
    fields = ("file", "preview", "icon_preview", "hls_ready", "hls_playlist")


class ServiceAttributeValueInline(nested_admin.NestedTabularInline):
    model = AttributeValue
    extra = 0
    fields = (
        'attribute',
        'value_text_tm', 'value_text_ru',
        'value_number', 'value_boolean',
    )


class ServiceProductImageInline(nested_admin.NestedTabularInline):
    model = ServiceProductImage
    extra = 0


class ServiceProductInline(nested_admin.NestedStackedInline):
    model = ServiceProduct
    extra = 0
    inlines = [ServiceAttributeValueInline, ServiceProductImageInline]


class ServiceAvailableCityInline(nested_admin.NestedTabularInline):
    model = Service.available_cities.through
    extra = 0
    verbose_name = 'Available City'
    verbose_name_plural = 'Available Cities'
    autocomplete_fields = ['city']
    fields = ('city',)
    can_delete = True


class ServiceAdminForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = "__all__"

    def clean(self):
        cleaned_data = super().clean()
        category = cleaned_data.get("category")
        additional_categories = cleaned_data.get("additional_categories")

        if category and additional_categories and additional_categories.filter(pk=category.pk).exists():
            self.add_error("additional_categories", "Primary category must not be duplicated.")

        if additional_categories and additional_categories.count() > 3:
            self.add_error("additional_categories", "No more than 3 additional categories are allowed.")

        return cleaned_data


@admin.register(Service)
class ServiceAdmin(nested_admin.NestedModelAdmin):
    form = ServiceAdminForm
    list_display = (
        'title_tm', 'vendor', 'category', 'additional_categories_list',
        'city', 'show_location', 'work_experience_years', 'is_active', 'is_verified', 'is_vip', 'priority'
    )
    list_filter = ('category', 'city', 'show_location', 'is_active', 'is_verified', 'is_vip')
    search_fields = ('title_tm', 'title_ru', 'vendor__name', 'category__name_tm')
    ordering = ('priority', '-created_at')
    filter_horizontal = ('regions', 'tags', 'additional_categories')
    inlines = [
        ServiceContactInline,
        ServiceImageInline,
        ServiceVideoInline,
        ServiceAvailableCityInline,
        ServiceProductInline,
    ]

    class Media:
        css = {
            "all": (
                "admin/css/service_map.css",
                "vendor/leaflet/leaflet.css",
            )
        }
        js = (
            "vendor/leaflet/leaflet.js",
            "admin/js/service_map.js",
        )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("additional_categories")

    def additional_categories_list(self, obj):
        return ", ".join(category.name_tm for category in obj.additional_categories.all())

    additional_categories_list.short_description = "Additional Categories"

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["osm_tile_url"] = getattr(settings, "OSM_TILE_URL", "")
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

    def add_view(self, request, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["osm_tile_url"] = getattr(settings, "OSM_TILE_URL", "")
        return super().add_view(request, form_url, extra_context=extra_context)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('service', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'service')
    search_fields = ('comment', 'user__name', 'service__title_tm')
    ordering = ('-created_at',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'get_target')
    search_fields = (
        'user__name',
        'service__title_tm', 'service__title_ru',
        'product__title_tm', 'product__title_ru',
    )

    def get_target(self, obj):
        return obj.service or obj.product
    get_target.short_description = 'Target'


@admin.register(ServiceTag)
class ServiceTagAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru')
    search_fields = ('name_tm', 'name_ru')


@admin.register(Attribute)
class ServiceAttributeAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'category', 'slug', 'input_type', 'is_required')
    list_filter = ('category', 'input_type')
    search_fields = ('name_tm', 'name_ru', 'slug')
#
#
# @admin.register(AttributeValue)
# class ServiceAttributeValueAdmin(admin.ModelAdmin):
#     list_display = ('product', 'attribute', 'get_display_value')
#     list_filter = ('attribute__category', 'attribute__input_type')
#     search_fields = (
#         'product__title_tm', 'product__title_ru', 'product__title_en',
#         'attribute__name_tm', 'attribute__name_ru', 'attribute__name_en',
#     )
#
#     def get_display_value(self, obj):
#         return obj.value
#     get_display_value.short_description = "Value"


@admin.register(ContactType)
class ContactTypeAdmin(IconPreviewMixin, admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru', 'icon_preview')
    search_fields = ('name_tm', 'name_ru')
    readonly_fields = ('slug',)


class ServiceApplicationImageInline(IconPreviewMixin, admin.TabularInline):
    model = ServiceApplicationImage
    extra = 0
    icon_field_name = 'image'
    icon_width = 80
    icon_height = 80
    readonly_fields = ('icon_preview',)
    fields = ('icon_preview', 'image',)


class ServiceApplicationLinkInline(admin.TabularInline):
    model = ServiceApplicationLink
    extra = 0
    fields = ("url",)


@admin.register(ServiceApplication)
class ServiceApplicationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'title', 'phone', 'email', 'category', 'category_name', 'city', 'city_name',
        'price_from', 'work_experience_years', 'status', 'created_at'
    )
    list_filter = ('status', 'category', 'city')
    search_fields = ('title', 'phone', 'email', 'description', 'contact_name', 'category_name', 'city_name', 'address')
    readonly_fields = ('created_at',)
    inlines = [ServiceApplicationLinkInline, ServiceApplicationImageInline]
