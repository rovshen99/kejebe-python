from django.utils.html import format_html


class IconPreviewMixin:
    icon_field_name = "icon"
    icon_width = 32
    icon_height = 32

    def icon_preview(self, obj):
        icon = getattr(obj, self.icon_field_name, None)
        if icon:
            return format_html(
                '<img src="{}" width="{}" height="{}" style="object-fit:contain;" />',
                icon.url, self.icon_width, self.icon_height
            )
        return "-"

    icon_preview.short_description = "Icon"
    icon_preview.allow_tags = True
