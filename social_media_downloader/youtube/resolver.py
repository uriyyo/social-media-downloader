import re
from asyncio import to_thread
from contextlib import suppress

from pytube import YouTube
from pytube.exceptions import AgeRestrictedError

from ..common import VideoMedia, find_all_by_regex, verify

YOUTUBE_LINK_REGEX = re.compile(
    r"https://(www\.)?(youtube\.com|youtu\.be)/[^\s\]\)]+",
    re.DOTALL | re.IGNORECASE,
)


def youtube_all_links(text: str) -> list[str]:
    return find_all_by_regex(YOUTUBE_LINK_REGEX, text)


def _sync_resolve_links(url: str, max_mb: float | None = None) -> VideoMedia | None:
    yt = YouTube(url)

    with suppress(AgeRestrictedError):
        for stream in yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc():
            if max_mb and stream.filesize_mb > max_mb:
                continue

            return VideoMedia(
                url=stream.url,
                thumbnail_url=yt.thumbnail_url,
            )

    return None


async def youtube_resolve_links(
    url: str,
    *,
    max_mb: float | None = None,
) -> VideoMedia:
    media = await to_thread(_sync_resolve_links, url, max_mb)

    return verify(media)


__all__ = [
    "youtube_all_links",
    "youtube_resolve_links",
]
