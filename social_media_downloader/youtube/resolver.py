import re
from typing import Any

from httpx import AsyncClient

from ..common import VideoMedia, find_all_by_regex, verify
from ..common.utils import httpx_client

YOUTUBE_LINK_REGEX = re.compile(
    r"https://(www\.)?(youtube\.com|youtu\.be)/[^\s\]\)]+",
    re.DOTALL | re.IGNORECASE,
)

_VIDSSAVE_API_URL = "https://api.vidssave.com/api/contentsite_api/media/parse"
_VIDSSAVE_AUTH = "20250901majwlqo"
_VIDSSAVE_DOMAIN = "api-ak.vidssave.com"


def youtube_all_links(text: str) -> list[str]:
    return find_all_by_regex(YOUTUBE_LINK_REGEX, text)


def _pick_best_video(data: dict[str, Any], max_mb: float | None = None) -> VideoMedia | None:
    resources = data.get("resources", [])
    thumbnail = data.get("thumbnail")

    videos = [r for r in resources if r.get("type") == "video" and r.get("format") == "MP4"]

    quality_order = ["1080P", "720P", "480P", "360P", "240P", "144P"]
    videos.sort(key=lambda v: quality_order.index(v["quality"]) if v["quality"] in quality_order else 999)

    for video in videos:
        if max_mb and video.get("size", 0) / (1024 * 1024) > max_mb:
            continue

        download_url = video.get("download_url")
        if download_url:
            return VideoMedia(url=download_url, thumbnail_url=thumbnail)

    return None


async def youtube_resolve_links(
    url: str,
    *,
    max_mb: float | None = None,
    client: AsyncClient | None = None,
) -> VideoMedia:
    async with httpx_client(client) as client:
        response = await client.post(
            _VIDSSAVE_API_URL,
            data={
                "auth": _VIDSSAVE_AUTH,
                "domain": _VIDSSAVE_DOMAIN,
                "origin": "source",
                "link": url,
            },
            headers={
                "referer": "https://vidssave.com/",
            },
        )
        response.raise_for_status()

        result = response.json()
        media = _pick_best_video(result.get("data", {}), max_mb)

    return verify(media)


__all__ = [
    "youtube_all_links",
    "youtube_resolve_links",
]
