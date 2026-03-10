import hashlib
import io
import logging
import os
from collections.abc import Iterable

from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.db import models
from django.utils.translation import gettext_lazy as _
from image_cropping import ImageRatioField
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel
from core.fields import WebPImageField

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None

logger = logging.getLogger(__name__)


class Category(MPTTModel):
    CATEGORY_IMAGE_THUMB_ALLOWED_SIZES = {(480, 360)}
    CATEGORY_IMAGE_THUMB_SIZE = (480, 360)
    CATEGORY_IMAGE_THUMB_QUALITY = 80

    name_tm = models.CharField(max_length=255)
    name_ru = models.CharField(max_length=255)

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

    def get_image_thumb_url(self, size: tuple[int, int] | str | None = None) -> str | None:
        thumb_size = self._normalize_thumb_size(size)
        if not thumb_size:
            return None
        thumb_name = self._ensure_image_thumb(thumb_size)
        if not thumb_name:
            return None
        try:
            return self.image.storage.url(thumb_name)
        except Exception:
            return None

    def save(self, *args, **kwargs):
        previous_image_name = None
        if self.pk:
            previous_image_name = (
                type(self).objects.filter(pk=self.pk).values_list("image", flat=True).first()
            ) or None

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

        current_image_name = self.image.name if self.image else None
        if self.pk and previous_image_name != current_image_name:
            self._cleanup_image_thumbs()

    def delete(self, *args, **kwargs):
        self._cleanup_image_thumbs()
        return super().delete(*args, **kwargs)

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
        base_name = os.path.basename(original_name)
        root, _ = os.path.splitext(base_name)
        if not root.endswith("_cropped"):
            root = f"{root}_cropped"
        return f"{root}.webp"

    def _normalize_thumb_size(self, size: tuple[int, int] | str | None) -> tuple[int, int] | None:
        if size is None:
            candidate = self.CATEGORY_IMAGE_THUMB_SIZE
        elif isinstance(size, str):
            parts = size.lower().split("x")
            if len(parts) != 2:
                return None
            try:
                candidate = (int(parts[0]), int(parts[1]))
            except ValueError:
                return None
        else:
            try:
                parts = tuple(size)
            except TypeError:
                return None
            if len(parts) != 2:
                return None
            try:
                candidate = (int(parts[0]), int(parts[1]))
            except (TypeError, ValueError):
                return None

        return candidate if candidate in self.CATEGORY_IMAGE_THUMB_ALLOWED_SIZES else None

    def _ensure_image_thumb(self, size: tuple[int, int]) -> str | None:
        if not self.image:
            return None
        if Image is None or ImageOps is None:
            return None

        thumb_name = self._build_image_thumb_name(size)
        storage = self.image.storage
        try:
            if storage.exists(thumb_name):
                return thumb_name
        except Exception:
            return None

        self._cleanup_image_thumbs(size=size, exclude_names={thumb_name})

        try:
            self.image.open("rb")
            with Image.open(self.image.file) as img:
                img.load()
                img = self._normalize_image_mode(img)
                resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
                thumb = ImageOps.fit(
                    img,
                    size,
                    method=resampling,
                )
                buffer = io.BytesIO()
                thumb.save(
                    buffer,
                    format="WEBP",
                    quality=self.CATEGORY_IMAGE_THUMB_QUALITY,
                    method=6,
                )
                buffer.seek(0)
                storage.save(thumb_name, ContentFile(buffer.read()))
            return thumb_name
        except Exception:
            return None
        finally:
            try:
                self.image.close()
            except Exception:
                pass

    def _build_image_thumb_name(self, size: tuple[int, int]) -> str:
        signature = self._build_image_signature()
        width, height = size
        return f"{self._get_image_thumb_prefix()}/thumb_{width}x{height}_{signature}.webp"

    def _build_image_signature(self) -> str:
        if not self.image:
            return "no-image"

        signature_parts = [self.image.name]
        try:
            signature_parts.append(str(self.image.size))
        except Exception:
            pass
        try:
            modified = self.image.storage.get_modified_time(self.image.name)
            signature_parts.append(str(int(modified.timestamp())))
        except Exception:
            pass

        raw = "|".join(signature_parts).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()[:16]

    def _get_image_thumb_prefix(self) -> str:
        object_id = self.pk or "tmp"
        return f"category/thumbs/{object_id}"

    def _cleanup_image_thumbs(
        self,
        size: tuple[int, int] | None = None,
        exclude_names: Iterable[str] | None = None,
    ) -> None:
        if not self.pk:
            return

        storage = self._meta.get_field("image").storage
        prefix = self._get_image_thumb_prefix()
        all_thumb_files = self._list_storage_files(storage, prefix)
        if not all_thumb_files:
            return

        excluded = set(exclude_names or [])
        filtered = all_thumb_files
        if size is not None:
            size_prefix = f"thumb_{size[0]}x{size[1]}_"
            filtered = [name for name in filtered if os.path.basename(name).startswith(size_prefix)]

        delete_candidates = [(storage, name) for name in filtered if name not in excluded]
        self._cleanup_old_files(delete_candidates)

    def _list_storage_files(self, storage: Storage, path: str) -> list[str]:
        try:
            dirs, files = storage.listdir(path)
        except Exception:
            return []

        normalized = path.rstrip("/")
        items = [f"{normalized}/{name}" for name in files]
        for dirname in dirs:
            child_path = f"{normalized}/{dirname}"
            items.extend(self._list_storage_files(storage, child_path))
        return items

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
