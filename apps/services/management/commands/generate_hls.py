import shutil
import subprocess
import tempfile
from pathlib import Path

from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.services.models import ServiceVideo


class Command(BaseCommand):
    help = "Generate HLS playlists for service videos."

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, dest="video_id", help="Process one ServiceVideo by id")
        parser.add_argument("--force", action="store_true", help="Re-generate HLS even if already ready")
        parser.add_argument(
            "--cleanup-originals",
            action="store_true",
            help="Delete original source files for videos where HLS is already ready.",
        )
        parser.add_argument("--limit", type=int, default=0, help="Limit number of videos")
        parser.add_argument(
            "--ffmpeg-bin",
            dest="ffmpeg_bin",
            default="",
            help="Custom ffmpeg binary path. Defaults to settings.FFMPEG_BIN or 'ffmpeg'.",
        )

    def handle(self, *args, **options):
        video_id = options.get("video_id")
        force = options.get("force", False)
        cleanup_originals = options.get("cleanup_originals", False)
        limit = options.get("limit", 0)

        if cleanup_originals:
            self._cleanup_originals(video_id=video_id, limit=limit)
            return

        ffmpeg_bin = self._resolve_ffmpeg_bin(options.get("ffmpeg_bin"))

        qs = ServiceVideo.objects.exclude(file="").exclude(file=None)
        if video_id:
            qs = qs.filter(pk=video_id)
        elif not force:
            qs = qs.filter(Q(hls_ready=False) | Q(preview="") | Q(preview=None))
        if limit:
            qs = qs[:limit]

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No videos to process."))
            return

        for video in qs:
            self._process_video(video, force, ffmpeg_bin)

    def _cleanup_originals(self, video_id=None, limit=0):
        qs = (
            ServiceVideo.objects.filter(hls_ready=True)
            .exclude(file="")
            .exclude(file=None)
        )
        if video_id:
            qs = qs.filter(pk=video_id)
        if limit:
            qs = qs[:limit]

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No original files to clean up."))
            return

        for video in qs:
            self._delete_original_file_if_configured(video)

    def _resolve_ffmpeg_bin(self, cli_value):
        candidate = (cli_value or getattr(settings, "FFMPEG_BIN", "") or "ffmpeg").strip()
        resolved = shutil.which(candidate)
        if resolved:
            return resolved
        raise CommandError(
            f"ffmpeg binary not found: {candidate!r}. "
            f"Install ffmpeg or set FFMPEG_BIN / --ffmpeg-bin to the full path."
        )

    def _process_video(self, video, force, ffmpeg_bin):
        needs_hls = force or not (video.hls_ready and video.hls_playlist)
        needs_preview = force or not getattr(video.preview, "name", None)

        if not needs_hls and not needs_preview:
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

                update_fields = []

                if needs_hls:
                    cmd = self._build_hls_cmd(
                        ffmpeg_bin=ffmpeg_bin,
                        source_path=source_path,
                        segment_pattern=segment_pattern,
                        playlist_path=playlist_path,
                    )

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
                    update_fields.extend(["hls_playlist", "hls_ready", "hls_error", "hls_updated_at"])

                if needs_preview:
                    try:
                        preview_path = tmpdir_path / "preview.jpg"
                        self._generate_preview(source_path, preview_path, ffmpeg_bin)
                        previous_preview_name = getattr(video.preview, "name", "")
                        with preview_path.open("rb") as preview_file:
                            video.preview.save(
                                f"service-video-{video.pk}-preview.jpg",
                                File(preview_file),
                                save=False,
                            )
                        if previous_preview_name and previous_preview_name != video.preview.name:
                            try:
                                default_storage.delete(previous_preview_name)
                            except Exception:
                                pass
                        update_fields.append("preview")
                    except Exception as preview_exc:
                        self.stdout.write(
                            self.style.WARNING(
                                f"Preview generation failed for ServiceVideo #{video.pk}: {preview_exc}"
                            )
                        )

                if update_fields:
                    video.save(update_fields=update_fields)
                self._delete_original_file_if_configured(video)
        except Exception as exc:
            video.hls_ready = False
            video.hls_error = str(exc)[:1000]
            video.hls_updated_at = timezone.now()
            video.save(update_fields=["hls_ready", "hls_error", "hls_updated_at"])
            self.stdout.write(self.style.ERROR(f"Failed for ServiceVideo #{video.pk}: {exc}"))

    def _delete_original_file_if_configured(self, video):
        if not getattr(settings, "DELETE_ORIGINAL_VIDEO_AFTER_HLS", True):
            return
        if not getattr(video, "hls_ready", False):
            return

        source_name = getattr(getattr(video, "file", None), "name", "") or ""
        if not source_name:
            return

        try:
            default_storage.delete(source_name)
            video.file = None
            video.save(update_fields=["file"])
            self.stdout.write(
                self.style.SUCCESS(f"Deleted original source for ServiceVideo #{video.pk}.")
            )
        except Exception as exc:
            self.stdout.write(
                self.style.WARNING(
                    f"Could not delete original source for ServiceVideo #{video.pk}: {exc}"
                )
            )

    @staticmethod
    def _build_hls_cmd(ffmpeg_bin, source_path, segment_pattern, playlist_path):
        return [
            ffmpeg_bin,
            "-y",
            "-i",
            str(source_path),
            "-c:v",
            "h264",
            # Normalize HDR/10-bit and other high-bit-depth sources for broad HLS compatibility.
            "-pix_fmt",
            "yuv420p",
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

    def _generate_preview(self, source_path, preview_path, ffmpeg_bin):
        candidates = ("1", "0.3")
        last_error = "ffmpeg failed to generate preview"

        for seek_time in candidates:
            cmd = [
                ffmpeg_bin,
                "-y",
                "-ss",
                seek_time,
                "-i",
                str(source_path),
                "-frames:v",
                "1",
                "-q:v",
                "2",
                str(preview_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0 and preview_path.exists() and preview_path.stat().st_size > 0:
                return
            last_error = result.stderr.strip() or last_error

        raise RuntimeError(last_error)
