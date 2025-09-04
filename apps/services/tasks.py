from __future__ import annotations

from pathlib import Path

from celery import shared_task
from django.conf import settings
from django.core.files.base import File

from apps.services.models import ServiceVideo
from core.video import transcode_to_hls, DEFAULT_RENDITIONS, Rendition


def _get_renditions_from_settings():
    cfg = getattr(settings, "HLS_RENDITIONS", None)
    if not cfg:
        return DEFAULT_RENDITIONS
    out: list[Rendition] = []
    for item in cfg:
        # each item: {"name": str, "width": int, "v_bitrate": int, "a_bitrate": int}
        out.append(Rendition(
            name=item.get("name"),
            width=int(item.get("width")),
            v_bitrate=int(item.get("v_bitrate")),
            a_bitrate=int(item.get("a_bitrate")),
        ))
    return out


@shared_task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 3})
def transcode_service_video_task(self, video_id: int):
    sv = ServiceVideo.objects.get(id=video_id)
    if not sv.file:
        return
    sv.transcode_status = ServiceVideo.TranscodeStatus.PROCESSING
    sv.save(update_fields=["transcode_status"])

    input_abs = Path(sv.file.path)
    out_dir = Path(settings.MEDIA_ROOT) / "services" / "hls" / str(sv.id)
    out_dir.mkdir(parents=True, exist_ok=True)

    transcode_to_hls(str(input_abs), str(out_dir), renditions=_get_renditions_from_settings())

    master_path = out_dir / "master.m3u8"
    if master_path.exists():
        rel_master_path = master_path.relative_to(settings.MEDIA_ROOT)
        with master_path.open("rb") as f:
            sv.hls_master.save(str(rel_master_path), File(f), save=False)
    sv.transcode_status = ServiceVideo.TranscodeStatus.READY
    sv.save(update_fields=["hls_master", "transcode_status"])

