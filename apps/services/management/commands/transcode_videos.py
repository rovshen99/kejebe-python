from __future__ import annotations

import os
from pathlib import Path

from django.core.files.base import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.conf import settings

from apps.services.models import ServiceVideo
from core.video import transcode_to_hls


class Command(BaseCommand):
    help = "Transcode pending/selected ServiceVideo files to HLS (requires ffmpeg)."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="Specific ServiceVideo ID to transcode", default=None)

    def handle(self, *args, **options):
        video_id = options["id"]
        qs = ServiceVideo.objects.all()
        if video_id is not None:
            qs = qs.filter(id=video_id)
        else:
            qs = qs.filter(transcode_status__in=[ServiceVideo.TranscodeStatus.PENDING, ServiceVideo.TranscodeStatus.FAILED])

        count = 0
        for sv in qs.iterator():
            if not sv.file:
                continue
            self.stdout.write(f"Processing video ID={sv.id} ...")
            try:
                with transaction.atomic():
                    sv.transcode_status = ServiceVideo.TranscodeStatus.PROCESSING
                    sv.save(update_fields=["transcode_status"])

                input_abs = Path(sv.file.path)
                target_dir = Path(settings.MEDIA_ROOT) / "services" / "hls" / str(sv.id)
                target_dir.mkdir(parents=True, exist_ok=True)

                transcode_to_hls(str(input_abs), str(target_dir))

                # Attach master playlist file to model
                master_path = target_dir / "master.m3u8"
                if not master_path.exists():
                    raise CommandError("master.m3u8 not found after transcode")

                # Save as FileField relative to MEDIA_ROOT via File()
                rel_master_path = master_path.relative_to(settings.MEDIA_ROOT)
                with master_path.open("rb") as f:
                    sv.hls_master.save(str(rel_master_path), File(f), save=False)

                sv.transcode_status = ServiceVideo.TranscodeStatus.READY
                sv.save(update_fields=["hls_master", "transcode_status"])
                count += 1
                self.stdout.write(self.style.SUCCESS(f"OK ID={sv.id}"))
            except Exception as e:
                sv.transcode_status = ServiceVideo.TranscodeStatus.FAILED
                sv.save(update_fields=["transcode_status"])
                self.stderr.write(self.style.ERROR(f"Failed ID={sv.id}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Done. Transcoded {count} video(s)."))

