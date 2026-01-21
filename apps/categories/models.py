import hashlib
import io
import logging
import os

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import models
from django.utils.translation import gettext_lazy as _
from image_cropping import ImageRatioField
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from core.fields import WebPImageField

try:
    from PIL import Image
except Exception:
    Image = None

logger = logging.getLogger(__name__)


class Category(MPTTModel):
    name_tm = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)
    name_en = models.CharField(max_length=255)

    parent = TreeForeignKey(
        "self",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_("Parent"),
    )

    slug = models.SlugField(
        max_length=64, unique=True, blank=True, null=True, verbose_name=_("Slug")
    )
    image = WebPImageField(
        upload_to="category/", verbose_name=_("Image"), null=True, default=None, blank=True, webp_quality=100,
    )
    image_cropping = ImageRatioField("image", "4x3")
    icon = WebPImageField(
        upload_to="category/icons/", verbose_name=_("Icon"), null=True, blank=True, default=None, webp_quality=100,
    )
    icon_cropping = ImageRatioField("icon", "1x1")
    image_crop_applied = models.CharField(max_length=128, blank=True, default="")
    icon_crop_applied = models.CharField(max_length=128, blank=True, default="")
    priority = models.PositiveIntegerField(default=100, verbose_name=_("Priority"))

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ("priority",)

    class MPTTMeta:
        order_insertion_by = ["name_tm"]

    def __str__(self):
        return self.name_tm

    def save(self, *args, **kwargs):
        pending_deletes: list[tuple[Storage, str]] = []
        pending_deletes += self._maybe_crop_field(
            field_name="image",
            crop_field_name="image_cropping",
            applied_field_name="image_crop_applied",
        )
        pending_deletes += self._maybe_crop_field(
            field_name="icon",
            crop_field_name="icon_cropping",
            applied_field_name="icon_crop_applied",
        )
        super().save(*args, **kwargs)
        self._cleanup_old_files(pending_deletes)

    def _maybe_crop_field(
        self, field_name: str, crop_field_name: str, applied_field_name: str
    ) -> list[tuple[Storage, str]]:
        field_file = getattr(self, field_name)
        crop_value = getattr(self, crop_field_name)

        if not field_file or not crop_value:
            return []

        if Image is None:
            logger.warning("Pillow is not available; skipping crop for %s", field_name)
            return []

        file_name = field_file.name or getattr(field_file.file, "name", "")
        if not file_name:
            return []

        signature_source = f"{file_name}|{crop_value}".encode("utf-8")
        signature = hashlib.sha256(signature_source).hexdigest()
        if signature == getattr(self, applied_field_name):
            return []

        old_name_in_memory = field_file.name
        old_name_in_db = None
        if self.pk:
            old_name_in_db = (
                type(self)
                .objects.filter(pk=self.pk)
                .values_list(field_name, flat=True)
                .first()
            )

        crop_box = self._parse_crop_value(crop_value)
        if not crop_box:
            return []

        cropped = self._crop_image(field_file, crop_box)
        if cropped is None:
            return []

        new_name = self._build_cropped_filename(file_name)
        buffer = io.BytesIO()
        cropped.save(buffer, format="WEBP", lossless=True, method=6, exact=True)
        buffer.seek(0)

        content = ContentFile(buffer.read())
        content.skip_webp_conversion = True
        field_file.save(new_name, content, save=False)
        new_full_name = field_file.name

        setattr(self, applied_field_name, signature)
        setattr(self, crop_field_name, "")

        delete_candidates = [old_name_in_memory, old_name_in_db]
        pending = []
        for name in delete_candidates:
            if not name or name == new_full_name:
                continue
            pending.append((field_file.storage, name))
        return pending

    def _parse_crop_value(self, crop_value: str) -> tuple[int, int, int, int] | None:
        parts = [part.strip() for part in crop_value.split(",")]
        if len(parts) != 4:
            return None
        try:
            x1, y1, x2, y2 = [int(float(value)) for value in parts]
        except ValueError:
            return None
        return x1, y1, x2, y2

    def _crop_image(self, field_file, crop_box: tuple[int, int, int, int]):
        try:
            field_file.open("rb")
            with Image.open(field_file.file) as img:
                img.load()
                img = self._normalize_image_mode(img)
                width, height = img.size
                x1, y1, x2, y2 = crop_box
                x1 = max(0, min(x1, width))
                x2 = max(0, min(x2, width))
                y1 = max(0, min(y1, height))
                y2 = max(0, min(y2, height))
                if x2 <= x1 or y2 <= y1:
                    return None
                return img.crop((x1, y1, x2, y2))
        except Exception:
            return None
        finally:
            try:
                field_file.close()
            except Exception:
                pass

    @staticmethod
    def _normalize_image_mode(img):
        if img.mode in ("RGBA", "LA", "P"):
            return img.convert("RGBA")
        if img.mode in ("CMYK", "L"):
            return img.convert("RGB")
        return img

    @staticmethod
    def _build_cropped_filename(original_name: str) -> str:
        dir_name = os.path.dirname(original_name)
        base_name = os.path.basename(original_name)
        root, _ = os.path.splitext(base_name)
        if not root.endswith("_cropped"):
            root = f"{root}_cropped"
        new_base = f"{root}.webp"
        return os.path.join(dir_name, new_base) if dir_name else new_base

    @staticmethod
    def _cleanup_old_files(names: list[tuple[Storage, str]]):
        seen = set()
        unique = []
        for storage, name in names:
            key = (id(storage), name)
            if not name or key in seen:
                continue
            seen.add(key)
            unique.append((storage, name))
        if not seen:
            return
        for storage, name in unique:
            try:
                if storage.exists(name):
                    storage.delete(name)
            except Exception:
                continue
