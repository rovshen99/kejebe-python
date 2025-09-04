import os
import shlex
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List

from django.conf import settings


@dataclass
class Rendition:
    name: str
    width: int
    v_bitrate: int  # in kbps
    a_bitrate: int  # in kbps


DEFAULT_RENDITIONS: List[Rendition] = [
    Rendition("1080p", 1920, 5400, 192),
    Rendition("720p", 1280, 3000, 160),
    Rendition("480p", 854, 1600, 128),
    Rendition("360p", 640, 800, 96),
]


def transcode_to_hls(input_abs: str, output_dir_abs: str, renditions: List[Rendition] | None = None) -> None:
    """Transcode a video file into multi-bitrate HLS with variant playlists and a master m3u8.

    Requires ffmpeg available in PATH. Produces MPEG-TS segments for compatibility.
    Output structure:
      output_dir/
        v0/playlist.m3u8, seg_*.ts
        v1/playlist.m3u8, seg_*.ts
        ...
        master.m3u8
    """
    renditions = renditions or DEFAULT_RENDITIONS

    input_path = Path(input_abs)
    output_root = Path(output_dir_abs)
    output_root.mkdir(parents=True, exist_ok=True)

    # Build filter_complex and mapping for all renditions
    n = len(renditions)
    split_labels = ";".join([f"[v{i}]" for i in range(n)])
    filter_parts = [f"[0:v]split={n}{split_labels}"]
    for i, r in enumerate(renditions):
        filter_parts.append(f"[v{i}]scale=w={r.width}:h=-2[v{i}out]")
    filter_complex = ";".join(filter_parts)

    args: list[str] = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_path),
        "-filter_complex",
        filter_complex,
    ]

    # Map each rendition with appropriate codec settings
    var_streams = []
    for i, r in enumerate(renditions):
        # video map
        args += [
            "-map",
            f"[v{i}out]",
            "-map",
            "0:a?",  # map audio if present
            f"-c:v:{i}",
            "h264",
            f"-profile:v:{i}",
            "main",
            f"-preset",
            "veryfast",
            f"-b:v:{i}",
            f"{r.v_bitrate}k",
            f"-maxrate:v:{i}",
            f"{int(r.v_bitrate*1.08)}k",
            f"-bufsize:v:{i}",
            f"{r.v_bitrate*2}k",
            f"-c:a:{i}",
            "aac",
            f"-b:a:{i}",
            f"{r.a_bitrate}k",
            f"-ac:{i}",
            "2",
        ]
        var_streams.append(f"v:{i},a:{i}")

    # HLS options
    args += [
        "-f",
        "hls",
        "-hls_time",
        "6",
        "-hls_playlist_type",
        "vod",
        "-hls_flags",
        "independent_segments",
        "-hls_segment_filename",
        str(output_root / "v%v" / "seg_%06d.ts"),
        "-master_pl_name",
        "master.m3u8",
        "-var_stream_map",
        " ".join(var_streams),
        str(output_root / "v%v" / "playlist.m3u8"),
    ]

    # Ensure subdirs like v0, v1 exist for segment writing
    for i in range(len(renditions)):
        (output_root / f"v{i}").mkdir(parents=True, exist_ok=True)

    # Run ffmpeg
    proc = subprocess.run(args, capture_output=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed (code {proc.returncode})\nSTDOUT: {proc.stdout.decode(errors='ignore')}\nSTDERR: {proc.stderr.decode(errors='ignore')}"
        )

