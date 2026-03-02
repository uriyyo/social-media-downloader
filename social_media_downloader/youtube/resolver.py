import re
from typing import Any

from httpx import AsyncClient

from ..common import VideoMedia, find_all_by_regex, verify
from ..common.utils import httpx_client

YOUTUBE_LINK_REGEX = re.compile(
    r"https://(www\.)?(youtube\.com|youtu\.be)/[^\s\]\)]+",
    re.DOTALL | re.IGNORECASE,
)

_GETLATE_API_URL = "https://getlate.dev/api/tools/youtube-video-downloader"

_QUALITY_ORDER = ["1080p", "720p", "480p", "360p", "240p", "144p"]


def youtube_all_links(text: str) -> list[str]:
    return find_all_by_regex(YOUTUBE_LINK_REGEX, text)


def _pick_best_format(formats: list[dict[str, Any]], max_mb: float | None = None) -> dict[str, Any] | None:
    with_audio = [f for f in formats if f.get("hasAudio") and f.get("hasVideo")]
    video_only = [f for f in formats if f.get("hasVideo") and not f.get("hasAudio")]

    for pool in [with_audio, video_only]:
        pool.sort(
            key=lambda f: _QUALITY_ORDER.index(f["label"]) if f["label"] in _QUALITY_ORDER else 999,
        )
        for fmt in pool:
            if max_mb and fmt.get("fileSize") and fmt["fileSize"] / (1024 * 1024) > max_mb:
                continue
            return fmt

    return None


async def youtube_resolve_links(
    url: str,
    *,
    max_mb: float | None = None,
    client: AsyncClient | None = None,
) -> VideoMedia:
    async with httpx_client(client) as client:
        # Step 1: Get available formats
        resp = await client.get(
            _GETLATE_API_URL,
            params={"action": "formats", "url": url},
        )
        resp.raise_for_status()
        data = resp.json()

        if not data.get("success"):
            msg = "Failed to get video formats"
            raise ValueError(msg)

        formats = verify(data.get("formats"), msg="No formats available")
        best = verify(_pick_best_format(formats, max_mb), msg="No suitable format found")

        # Step 2: Build download URL (returns 302 to googlevideo)
        # Return the proxy URL directly - googlevideo URLs are IP-locked,
        # so the consumer must follow the redirect chain from their own IP.
        download_url = str(
            client.build_request(
                "GET",
                _GETLATE_API_URL,
                params={"action": "download", "url": url, "formatId": best["id"]},
            ).url,
        )
        thumbnail = data.get("cover")

    return VideoMedia(url=download_url, thumbnail_url=thumbnail)


__all__ = [
    "youtube_all_links",
    "youtube_resolve_links",
]
