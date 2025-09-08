import nested_admin

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
)


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
    model = AttributeValue
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
    inlines = [ServiceAttributeValueInline, ServiceProductImageInline]


class ServiceAvailableCityInline(admin.TabularInline):
    model = Service.available_cities.through
    extra = 0
    verbose_name = 'Available City'
    verbose_name_plural = 'Available Cities'
    autocomplete_fields = ['city']
    fields = ('city',)
    can_delete = True


@admin.register(Service)
class ServiceAdmin(nested_admin.NestedModelAdmin):
    list_display = ('title_tm', 'vendor', 'category', 'city', 'is_active', 'priority')
    list_filter = ('category', 'city', 'is_active')
    search_fields = ('title_tm', 'title_ru', 'title_en', 'vendor__name', 'category__name_tm')
    ordering = ('priority', '-created_at')
    filter_horizontal = ('regions',)
    inlines = [
        ServiceContactInline,
        ServiceImageInline,
        ServiceVideoInline,
        ServiceAvailableCityInline,
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
    list_display = ('user', 'get_target')
    search_fields = (
        'user__name',
        'service__title_tm', 'service__title_ru', 'service__title_en',
        'product__title_tm', 'product__title_ru', 'product__title_en',
    )

    def get_target(self, obj):
        return obj.service or obj.product
    get_target.short_description = 'Target'


class ServiceInline(admin.TabularInline):
    model = Service.tags.through
    extra = 1


# @admin.register(ServiceTag)
# class ServiceTagAdmin(admin.ModelAdmin):
#     list_display = ('name_tm', 'name_ru', 'name_en')
#     search_fields = ('name_tm', 'name_ru', 'name_en')
#     inlines = [ServiceInline]


@admin.register(Attribute)
class ServiceAttributeAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'category', 'slug', 'input_type', 'is_required')
    list_filter = ('category', 'input_type')
    search_fields = ('name_tm', 'name_ru', 'name_en', 'slug')
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
    list_display = ('name_tm', 'name_ru', 'name_en', 'icon_preview')
    search_fields = ('name_tm', 'name_ru', 'name_en')
    readonly_fields = ('slug',)


class ServiceApplicationImageInline(IconPreviewMixin, admin.TabularInline):
    model = ServiceApplicationImage
    extra = 0
    icon_field_name = 'image'
    icon_width = 80
    icon_height = 80
    readonly_fields = ('icon_preview',)
    fields = ('icon_preview', 'image',)


@admin.register(ServiceApplication)
class ServiceApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'phone', 'category', 'city', 'status', 'created_at')
    list_filter = ('status', 'category', 'city')
    search_fields = ('title', 'phone', 'description', 'contact_name')
    readonly_fields = ('created_at',)
    inlines = [ServiceApplicationImageInline]
