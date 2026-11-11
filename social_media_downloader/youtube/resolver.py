import asyncio
import re
import tempfile
from pathlib import Path
from typing import Any

from httpx import AsyncClient
from yt_dlp import YoutubeDL

from ..common import RawMedia, ResolverConfig, find_all_by_regex, verify

YOUTUBE_LINK_REGEX = re.compile(
    r"https://(www\.)?(youtube\.com|youtu\.be)/[^\s\]\)]+",
    re.DOTALL | re.IGNORECASE,
)

_MAX_HEIGHT = 1080


def youtube_all_links(text: str) -> list[str]:
    return find_all_by_regex(YOUTUBE_LINK_REGEX, text)


def _size(fmt: dict[str, Any]) -> int | None:
    return fmt.get("filesize") or fmt.get("filesize_approx")


def _fits(size: int | None, max_mb: float | None) -> bool:
    return max_mb is None or (size is not None and size <= max_mb * 1024 * 1024)


def _pick_formats(formats: list[dict[str, Any]], max_mb: float | None = None) -> str:
    # YouTube mostly serves video and audio as separate streams,
    # so pick best h264 video + m4a audio and let ffmpeg merge them into mp4
    audios = [f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") == "none"]
    videos = [
        f
        for f in formats
        if f.get("vcodec") not in (None, "none") and f.get("acodec") == "none" and (f.get("height") or 0) <= _MAX_HEIGHT
    ]

    audio = max(audios, key=lambda f: (f.get("ext") == "m4a", f.get("abr") or 0), default=None)
    audio = verify(audio, msg="No audio formats available")

    videos.sort(
        key=lambda f: (
            f.get("protocol") == "https",
            (f.get("vcodec") or "").startswith("avc1"),
            f.get("height") or 0,
            f.get("tbr") or 0,
        ),
        reverse=True,
    )

    for video in videos:
        if _fits((_size(video) or 0) + (_size(audio) or 0) or None, max_mb):
            return f"{video['format_id']}+{audio['format_id']}"

    msg = "No suitable format found"
    raise ValueError(msg)


def _download(url: str, max_mb: float | None, config: ResolverConfig) -> bytes:
    with tempfile.TemporaryDirectory() as tmp:
        options = {
            "quiet": True,
            "no_warnings": True,
            "noprogress": True,
            "noplaylist": True,
            "merge_output_format": "mp4",
            "outtmpl": str(Path(tmp) / "video.%(ext)s"),
            "socket_timeout": config.timeout,
        }

        with YoutubeDL(options) as ydl:
            info = verify(ydl.extract_info(url, download=False), msg=f"Failed to extract info for {url}")

        options["format"] = _pick_formats(info.get("formats") or [], max_mb)

        with YoutubeDL(options) as ydl:
            ydl.process_ie_result(info, download=True)

        path = verify(next(Path(tmp).glob("video.*"), None), msg=f"Failed to download {url}")
        return path.read_bytes()


async def youtube_resolve_links(
    url: str,
    *,
    max_mb: float | None = None,
    config: ResolverConfig | None = None,
    client: AsyncClient | None = None,
) -> RawMedia:
    config = config or ResolverConfig.default()
    content = await asyncio.to_thread(_download, url, max_mb, config)

    return RawMedia(content=content, content_type="video/mp4")


__all__ = [
    "youtube_all_links",
    "youtube_resolve_links",
]
