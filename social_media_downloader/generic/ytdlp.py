import asyncio
from typing import Any

from httpx import AsyncClient
from yt_dlp import YoutubeDL

from ..common import ImageMedia, ResolverConfig, VideoMedia, verify


def _extract_info(url: str, config: ResolverConfig) -> dict[str, Any]:
    options = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": False,
        "format": "best",
        "socket_timeout": config.timeout,
    }

    with YoutubeDL(options) as ydl:
        info = ydl.extract_info(url, download=False)

    return verify(ydl.sanitize_info(info), msg=f"Failed to extract info for {url}")


def _parse_entry(entry: dict[str, Any]) -> ImageMedia | VideoMedia | None:
    if not (url := entry.get("url")):
        return None

    if entry.get("vcodec") == "none" and entry.get("acodec") == "none":
        return ImageMedia(url=url)

    return VideoMedia(
        url=url,
        thumbnail_url=entry.get("thumbnail"),
    )


async def ytdlp_resolve_links(
    url: str,
    *,
    config: ResolverConfig | None = None,
    client: AsyncClient | None = None,
) -> list[ImageMedia | VideoMedia]:
    config = config or ResolverConfig.default()
    info = await asyncio.to_thread(_extract_info, url, config)

    entries = info.get("entries") or [info]
    medias = [media for entry in entries if entry and (media := _parse_entry(entry))]

    return verify(medias, msg=f"No media found for {url}")


__all__ = [
    "ytdlp_resolve_links",
]
