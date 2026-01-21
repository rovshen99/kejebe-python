from django.contrib.admin.widgets import AdminFileWidget
from image_cropping import widgets
from image_cropping.backends.easy_thumbs import EasyThumbnailsBackend


class SafeImageCropWidget(widgets.ImageCropWidget):
    def render(self, name, value, attrs=None, renderer=None):
        if not attrs:
            attrs = {}
        if value:
            try:
                attrs.update(widgets.get_attrs(value, name))
            except (FileNotFoundError, OSError):
                pass
        render_args = [name, value, attrs]
        if renderer:
            render_args.append(renderer)
        return AdminFileWidget.render(self, *render_args)


class WebPEasyThumbnailsBackend(EasyThumbnailsBackend):
    WIDGETS = {
        **EasyThumbnailsBackend.WIDGETS,
        "ImageField": SafeImageCropWidget,
        "ImageCropField": SafeImageCropWidget,
        "WebPImageField": SafeImageCropWidget,
    }
