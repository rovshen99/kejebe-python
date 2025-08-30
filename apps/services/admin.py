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
    ServiceAttribute,
    ServiceAttributeValue, ContactType, ServiceProductImage, ServiceProduct
)

import nested_admin


class ServiceContactInline(nested_admin.NestedTabularInline):
    model = ServiceContact
    extra = 1


class ServiceImageInline(nested_admin.NestedTabularInline):
    model = ServiceImage
    extra = 1


class ServiceVideoInline(nested_admin.NestedTabularInline):
    model = ServiceVideo
    extra = 1


class ServiceAttributeValueInline(nested_admin.NestedTabularInline):
    model = ServiceAttributeValue
    extra = 0
    fields = (
        'attribute',
        'value_text_tm', 'value_text_ru', 'value_text_en',
        'value_number', 'value_boolean',
    )


class ServiceProductImageInline(nested_admin.NestedTabularInline):
    model = ServiceProductImage
    extra = 0


class ServiceProductInline(nested_admin.NestedStackedInline):
    model = ServiceProduct
    extra = 0
    inlines = [ServiceProductImageInline]


@admin.register(Service)
class ServiceAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title_tm', 'vendor', 'category', 'is_active', 'priority')
    list_filter = ('category', 'is_active')
    search_fields = ('title_tm', 'title_ru', 'title_en', 'vendor__name', 'category__name_tm')
    ordering = ('priority', '-created_at')
    filter_horizontal = ('cities', 'regions')
    inlines = [
        ServiceContactInline,
        ServiceImageInline,
        ServiceVideoInline,
        ServiceAttributeValueInline,
        ServiceProductInline,
    ]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('service', 'user', 'rating', 'created_at')
    list_filter = ('rating', 'service')
    search_fields = ('comment', 'user__name', 'service__title_tm')
    ordering = ('-created_at',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'service')
    search_fields = ('user__name', 'service__title_tm')


class ServiceInline(admin.TabularInline):
    model = Service.tags.through
    extra = 1


@admin.register(ServiceTag)
class ServiceTagAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru', 'name_en')
    search_fields = ('name_tm', 'name_ru', 'name_en')
    inlines = [ServiceInline]


@admin.register(ServiceAttribute)
class ServiceAttributeAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'category', 'slug', 'input_type', 'is_required')
    list_filter = ('category', 'input_type')
    search_fields = ('name_tm', 'name_ru', 'name_en', 'slug')


@admin.register(ServiceAttributeValue)
class ServiceAttributeValueAdmin(admin.ModelAdmin):
    list_display = ('service', 'attribute', 'get_display_value')
    list_filter = ('attribute__category', 'attribute__input_type')
    search_fields = ('service__title_tm', 'attribute__name_tm')

    def get_display_value(self, obj):
        return obj.value
    get_display_value.short_description = "Value"


@admin.register(ContactType)
class ContactTypeAdmin(IconPreviewMixin, admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru', 'name_en', 'icon_preview')
    search_fields = ('name_tm', 'name_ru', 'name_en')
    readonly_fields = ('slug',)

