from django.contrib import admin
from image_cropping import ImageCroppingMixin
from mptt.admin import DraggableMPTTAdmin
from .models import Category
from django.utils.translation import gettext_lazy as _


@admin.register(Category)
class CategoryAdmin(ImageCroppingMixin, DraggableMPTTAdmin):
    mptt_indent_field = "name_tm"
    list_display = (
        'tree_actions',
        'indented_title',
        'slug',
        'priority',
        'parent',
        'has_image',
        'has_icon',
    )
    list_display_links = ('indented_title',)
    list_filter = ('parent',)
    search_fields = ('name_tm', 'name_ru', 'name_en', 'slug')
    prepopulated_fields = {'slug': ('name_tm',)}
    ordering = ('priority',)

    def indented_title(self, instance):
        return instance.name_tm
    indented_title.short_description = _("Name (TM)")

    def has_image(self, obj):
        return bool(obj.image)
    has_image.boolean = True
    has_image.short_description = _("Image")

    def has_icon(self, obj):
        return bool(obj.icon)
    has_icon.boolean = True
    has_icon.short_description = _("Icon")
