import hashlib
import io
import os
from dataclasses import dataclass
from typing import Iterable, Optional

from django.core.files.base import ContentFile

try:
    from PIL import Image, ImageOps
except Exception:
    Image = None
    ImageOps = None


@dataclass(frozen=True)
class ImagePreset:
    key: str
    width: int
    height: int
    quality: int = 80


# Universal preset whitelist for home blocks.
HOME_IMAGE_PRESETS = {
    "banner_1x": ImagePreset("banner_1x", 1200, 675, 80),
    "banner_2x": ImagePreset("banner_2x", 2400, 1350, 80),
    "category_card_1x": ImagePreset("category_card_1x", 480, 360, 80),
    "category_card_2x": ImagePreset("category_card_2x", 960, 720, 80),
    "category_icon_1x": ImagePreset("category_icon_1x", 120, 120, 80),
    "category_icon_2x": ImagePreset("category_icon_2x", 240, 240, 80),
    # "story_avatar_1x": ImagePreset("story_avatar_1x", 120, 120, 80),
    # "story_avatar_2x": ImagePreset("story_avatar_2x", 240, 240, 80),
    # "story_cover_1x": ImagePreset("story_cover_1x", 360, 640, 80),
    # "story_cover_2x": ImagePreset("story_cover_2x", 720, 1280, 80),
    # "service_avatar_1x": ImagePreset("service_avatar_1x", 160, 160, 80),
    # "service_avatar_2x": ImagePreset("service_avatar_2x", 320, 320, 80),
    # "service_cover_1x": ImagePreset("service_cover_1x", 720, 540, 80),
    # "service_cover_2x": ImagePreset("service_cover_2x", 1440, 1080, 80),
    # "service_image_1x": ImagePreset("service_image_1x", 720, 540, 80),
    # "service_image_2x": ImagePreset("service_image_2x", 1440, 1080, 80),
}


def build_image_asset(
    source_field,
    *,
    entity: str,
    object_id: int,
    field_name: str,
    preset_keys: Iterable[str],
) -> Optional[dict]:
    if not source_field:
        return None
    try:
        original_url = source_field.url
    except Exception:
        return None
    if not original_url:
        return None

    variants = {}
    for key in preset_keys:
        preset = HOME_IMAGE_PRESETS.get(key)
        if not preset:
            continue
        variant_url = _ensure_variant_url(
            source_field=source_field,
            entity=entity,
            object_id=object_id,
            field_name=field_name,
            preset=preset,
        )
        if variant_url:
            variants[key] = variant_url
    return {"original": original_url, "variants": variants}


def _ensure_variant_url(source_field, *, entity: str, object_id: int, field_name: str, preset: ImagePreset) -> Optional[str]:
    variant_name = _build_variant_name(
        source_field=source_field,
        entity=entity,
        object_id=object_id,
        field_name=field_name,
        preset=preset,
    )
    storage = source_field.storage
    try:
        if storage.exists(variant_name):
            return storage.url(variant_name)
    except Exception:
        return None

    _cleanup_old_preset_variants(
        storage=storage,
        prefix=_build_field_prefix(entity=entity, object_id=object_id, field_name=field_name),
        preset_key=preset.key,
        keep_name=variant_name,
    )

    if Image is None or ImageOps is None:
        return None

    try:
        source_field.open("rb")
        with Image.open(source_field.file) as image:
            image.load()
            image = _normalize_mode(image)
            resampling = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
            rendered = ImageOps.fit(
                image,
                (preset.width, preset.height),
                method=resampling,
            )
            buffer = io.BytesIO()
            rendered.save(
                buffer,
                format="WEBP",
                quality=preset.quality,
                method=6,
            )
            buffer.seek(0)
            storage.save(variant_name, ContentFile(buffer.read()))
        return storage.url(variant_name)
    except Exception:
        return None
    finally:
        try:
            source_field.close()
        except Exception:
            pass


def _build_field_prefix(*, entity: str, object_id: int, field_name: str) -> str:
    return f"home/variants/{entity}/{object_id}/{field_name}"


def _build_variant_name(source_field, *, entity: str, object_id: int, field_name: str, preset: ImagePreset) -> str:
    signature = _source_signature(source_field)
    prefix = _build_field_prefix(entity=entity, object_id=object_id, field_name=field_name)
    return f"{prefix}/{preset.key}_{signature}.webp"


def _source_signature(source_field) -> str:
    parts = [source_field.name]
    try:
        parts.append(str(source_field.size))
    except Exception:
        pass
    try:
        modified = source_field.storage.get_modified_time(source_field.name)
        parts.append(str(int(modified.timestamp())))
    except Exception:
        pass
    raw = "|".join(parts).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _normalize_mode(image):
    if image.mode in ("RGBA", "LA", "P"):
        return image.convert("RGBA")
    if image.mode in ("CMYK", "L"):
        return image.convert("RGB")
    return image


def _cleanup_old_preset_variants(*, storage, prefix: str, preset_key: str, keep_name: str) -> None:
    candidates = _list_storage_files(storage, prefix)
    if not candidates:
        return
    marker = f"{preset_key}_"
    for name in candidates:
        base = os.path.basename(name)
        if not base.startswith(marker):
            continue
        if name == keep_name:
            continue
        try:
            if storage.exists(name):
                storage.delete(name)
        except Exception:
            continue


def _list_storage_files(storage, path: str) -> list[str]:
    try:
        dirs, files = storage.listdir(path)
    except Exception:
        return []

    normalized = path.rstrip("/")
    items = [f"{normalized}/{name}" for name in files]
    for dirname in dirs:
        child_path = f"{normalized}/{dirname}"
        items.extend(_list_storage_files(storage, child_path))
    return items
