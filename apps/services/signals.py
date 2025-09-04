from __future__ import annotations

import threading
from pathlib import Path

from django.conf import settings
from django.core.files.base import File
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.services.models import ServiceVideo
from .tasks import transcode_service_video_task


@receiver(post_save, sender=ServiceVideo)
def service_video_post_save(sender, instance: ServiceVideo, created, **kwargs):
    if instance.file and (created or instance.transcode_status == ServiceVideo.TranscodeStatus.PENDING):
        # Enqueue Celery task
        transcode_service_video_task.delay(instance.id)
