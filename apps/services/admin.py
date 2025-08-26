from django.contrib import admin
from .models import (
    Service,
    ServiceContact,
    ServiceImage,
    ServiceVideo,
    Review,
    Favorite,
    ServiceTag,
    ServiceAttribute,
    ServiceAttributeValue, ContactType
)


class ServiceContactInline(admin.TabularInline):
    model = ServiceContact
    extra = 1


class ServiceImageInline(admin.TabularInline):
    model = ServiceImage
    extra = 1


class ServiceVideoInline(admin.TabularInline):
    model = ServiceVideo
    extra = 1


class ServiceAttributeValueInline(admin.TabularInline):
    model = ServiceAttributeValue
    extra = 1
    fields = (
        'attribute',
        'value_text_tm', 'value_text_ru', 'value_text_en',
        'value_number', 'value_boolean',
    )


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('title_tm', 'vendor', 'category', 'is_active', 'priority')
    list_filter = ('category', 'is_active')
    search_fields = ('title_tm', 'title_ru', 'title_en', 'vendor__name', 'category__name_tm')
    ordering = ('priority', '-created_at')
    filter_horizontal = ('cities', 'regions')
    inlines = [ServiceContactInline, ServiceImageInline, ServiceVideoInline, ServiceAttributeValueInline]


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


@admin.register(ServiceTag)
class ServiceTagAdmin(admin.ModelAdmin):
    list_display = ('name_tm', 'name_ru', 'name_en')
    search_fields = ('name_tm', 'name_ru', 'name_en')


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
class ContactTypeAdmin(admin.ModelAdmin):
    list_display = ('slug', 'name_tm', 'name_ru', 'name_en', 'icon_preview')
    search_fields = ('slug', 'name_tm', 'name_ru', 'name_en')

    def icon_preview(self, obj):
        if obj.icon:
            return f'<img src="{obj.icon.url}" width="32" height="32" style="object-fit:contain;" />'
        return "-"
    icon_preview.short_description = "Icon"
    icon_preview.allow_tags = True
