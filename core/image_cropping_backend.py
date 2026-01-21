from image_cropping import widgets
from image_cropping.backends.easy_thumbs import EasyThumbnailsBackend


class WebPEasyThumbnailsBackend(EasyThumbnailsBackend):
    WIDGETS = {
        **EasyThumbnailsBackend.WIDGETS,
        "WebPImageField": widgets.ImageCropWidget,
    }
