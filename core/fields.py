import io
import os
from typing import Optional

from django.core.files.base import ContentFile
from django.db.models.fields.files import ImageField, ImageFieldFile

try:
    from PIL import Image
except Exception:
    Image = None


class WebPImageFieldFile(ImageFieldFile):
    def _convert_to_webp(self, name: str, content) -> tuple[str, Optional[ContentFile]]:
        if Image is None:
            return name, None

        if getattr(content, "skip_webp_conversion", False):
            return name, None

        lower = name.lower()
        if lower.endswith(".svg") and not getattr(self.field, "convert_svg", False):
            return name, None

        try:
            img = Image.open(content)

            if img.mode in ("RGBA", "LA", "P"):
                img = img.convert("RGBA")
            elif img.mode == "CMYK":
                img = img.convert("RGB")

            buf = io.BytesIO()
            quality = int(getattr(self.field, "webp_quality", 75))

            img.save(buf, format="WEBP", quality=quality, method=6)
            buf.seek(0)

            base, _ = os.path.splitext(name)
            new_name = f"{base}.webp"
            return new_name, ContentFile(buf.read())

        except Exception:
            return name, None

    def save(self, name, content, save=True):
        new_name, new_content = self._convert_to_webp(name, content)
        super().save(new_name, new_content or content, save)


class WebPImageField(ImageField):
    attr_class = WebPImageFieldFile

    def __init__(self, *args, webp_quality: int = 75, convert_svg: bool = False, **kwargs):
        self.webp_quality = webp_quality
        self.convert_svg = convert_svg
        super().__init__(*args, **kwargs)
