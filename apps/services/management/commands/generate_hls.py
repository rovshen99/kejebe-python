import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.services.models import ServiceVideo


class Command(BaseCommand):
    help = "Generate HLS playlists for service videos."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, dest="video_id", help="Process one ServiceVideo by id")
        parser.add_argument("--force", action="store_true", help="Re-generate HLS even if already ready")
        parser.add_argument("--limit", type=int, default=0, help="Limit number of videos")

    def handle(self, *args, **options):
        video_id = options.get("video_id")
        force = options.get("force", False)
        limit = options.get("limit", 0)

        qs = ServiceVideo.objects.exclude(file="").exclude(file=None)
        if video_id:
            qs = qs.filter(pk=video_id)
        elif not force:
            qs = qs.filter(hls_ready=False)
        if limit:
            qs = qs[:limit]

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No videos to process."))
            return

        for video in qs:
            self._process_video(video, force)

    def _process_video(self, video, force):
        if not force and video.hls_ready and video.hls_playlist:
            return
        if not video.file:
            return

        try:
            self.stdout.write(f"Processing ServiceVideo #{video.pk}...")
            with tempfile.TemporaryDirectory() as tmpdir:
                tmpdir_path = Path(tmpdir)
                source_path = tmpdir_path / "source"
                with default_storage.open(video.file.name, "rb") as src, source_path.open("wb") as dst:
                    shutil.copyfileobj(src, dst)

                hls_dir = tmpdir_path / "hls"
                hls_dir.mkdir(parents=True, exist_ok=True)
                playlist_name = "index.m3u8"
                segment_pattern = str(hls_dir / "seg_%03d.ts")
                playlist_path = hls_dir / playlist_name

                cmd = [
                    "ffmpeg",
                    "-y",
                    "-i",
                    str(source_path),
                    "-c:v",
                    "h264",
                    "-profile:v",
                    "main",
                    "-preset",
                    "veryfast",
                    "-crf",
                    "22",
                    "-c:a",
                    "aac",
                    "-b:a",
                    "128k",
                    "-ac",
                    "2",
                    "-g",
                    "48",
                    "-keyint_min",
                    "48",
                    "-sc_threshold",
                    "0",
                    "-hls_time",
                    "4",
                    "-hls_playlist_type",
                    "vod",
                    "-hls_segment_filename",
                    segment_pattern,
                    str(playlist_path),
                ]

                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or "ffmpeg failed")

                base_key = f"services/videos/hls/{video.pk}"
                for file_path in hls_dir.iterdir():
                    storage_path = f"{base_key}/{file_path.name}"
                    with file_path.open("rb") as fh:
                        default_storage.save(storage_path, File(fh))

                video.hls_playlist = f"{base_key}/{playlist_name}"
                video.hls_ready = True
                video.hls_error = ""
                video.hls_updated_at = timezone.now()
                video.save(update_fields=["hls_playlist", "hls_ready", "hls_error", "hls_updated_at"])
        except Exception as exc:
            video.hls_ready = False
            video.hls_error = str(exc)[:1000]
            video.hls_updated_at = timezone.now()
            video.save(update_fields=["hls_ready", "hls_error", "hls_updated_at"])
            self.stdout.write(self.style.ERROR(f"Failed for ServiceVideo #{video.pk}: {exc}"))
