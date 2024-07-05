import logging
import re
from typing import Literal, TypeAlias, overload

from httpx import AsyncClient

from ..common import AudioMedia, ImageMedia, VideoMedia, verify
from ..common.utils import find_all_by_regex, httpx_client
from ..generic.resolver import generic_resolve_links

logger = logging.getLogger(__name__)

AnyMedia: TypeAlias = VideoMedia | ImageMedia | AudioMedia

TOKEN_REGEX = re.compile(r"s_tt\s*=\s*'(.*?)'")

TIKTOK_LINK_REGEX = re.compile(
    r"https://(vm|www)\.tiktok\.com/[@\w+/]+/?",
    re.DOTALL | re.IGNORECASE,
)


def tiktok_all_links(text: str) -> list[str]:
    return find_all_by_regex(TIKTOK_LINK_REGEX, text)


async def _resolve_thumbnail(
    url: str,
    client: AsyncClient,
) -> str:
    response = await client.get(url)
    response.raise_for_status()

    *_, video_id = response.url.path.removesuffix("/").rsplit("/")

    response = await client.get(
        "https://www.tiktok.com/oembed",
        params={"url": f"https://www.tiktok.com/@tiktok/video/{video_id}"},
    )
    response.raise_for_status()

    return verify(response.json().get("thumbnail_url"))


async def _find_links(
    client: AsyncClient,
    url: str,
    *,
    images_as_video: bool = False,
    add_thumbnail: bool = False,
) -> VideoMedia | list[AnyMedia]:
    medias = await generic_resolve_links(
        url,
        client=client,
    )

    videos = [m for m in medias if isinstance(m, VideoMedia)]
    non_videos = [m for m in medias if not isinstance(m, VideoMedia)]

    verify(len(videos) == 1, msg="Expected exactly one video media")
    (video,) = videos

    if add_thumbnail:
        if non_videos:
            video.thumbnail_url = non_videos[0].url
        else:
            video.thumbnail_url = await _resolve_thumbnail(url, client)

    if images_as_video:
        return video

    return [video, *non_videos]


@overload
async def tiktok_resolve_links(
    url: str,
    *,
    images_as_video: Literal[True] = True,
    add_thumbnail: bool = False,
    client: AsyncClient | None = None,
) -> VideoMedia:
    pass


@overload
async def tiktok_resolve_links(
    url: str,
    *,
    images_as_video: Literal[False],
    add_thumbnail: bool = False,
    client: AsyncClient | None = None,
) -> list[AnyMedia]:
    pass


async def tiktok_resolve_links(
    url: str,
    *,
    images_as_video: bool = True,
    add_thumbnail: bool = False,
    client: AsyncClient | None = None,
) -> VideoMedia | list[AnyMedia]:
    async with httpx_client(client) as client:
        return await _find_links(
            client,
            url,
            images_as_video=images_as_video,
            add_thumbnail=add_thumbnail,
        )


async def tiktok_is_video(
    url: str,
    *,
    client: AsyncClient | None = None,
) -> bool:
    async with httpx_client(client) as client:
        response = await client.get(url)
        response.raise_for_status()

        return "/video/" in response.url.path


__all__ = [
    "tiktok_is_video",
    "tiktok_all_links",
    "tiktok_resolve_links",
]
