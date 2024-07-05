import logging
import re
from typing import Literal, TypeAlias, overload

from bs4 import BeautifulSoup
from httpx import AsyncClient, Response

from ..common import AudioMedia, ImageMedia, VideoMedia, verify
from ..common.utils import find_all_by_regex, httpx_client

logger = logging.getLogger(__name__)

AnyMedia: TypeAlias = VideoMedia | ImageMedia | AudioMedia

TOKEN_REGEX = re.compile(r"s_tt\s*=\s*'(.*?)'")

TIKTOK_LINK_REGEX = re.compile(
    r"https://(vm|www)\.tiktok\.com/[@\w+/]+/?",
    re.DOTALL | re.IGNORECASE,
)


def tiktok_all_links(text: str) -> list[str]:
    return find_all_by_regex(TIKTOK_LINK_REGEX, text)


async def _handle_video(
    client: AsyncClient,
    response: Response,
    *,
    add_thumbnail: bool = False,
) -> VideoMedia:
    root = BeautifulSoup(response.text, "html.parser")
    url = verify(root.select_one("a.download_link")).attrs["href"]
    thumbnail = None

    if add_thumbnail:
        *_, video_id = url.removesuffix("/").rsplit("/")

        response = await client.get(
            "https://www.tiktok.com/oembed",
            params={"url": f"https://www.tiktok.com/@tiktok/video/{video_id}"},
        )
        response.raise_for_status()

        thumbnail = verify(response.json().get("thumbnail_url"))

    return VideoMedia(
        url=url,
        thumbnail_url=thumbnail,
    )


async def _handle_images(
    client: AsyncClient,
    response: Response,
    *,
    resolve_image_video: bool = False,
    images_as_video: bool = False,
) -> VideoMedia | list[AnyMedia]:
    root = BeautifulSoup(response.text, "html.parser")

    images = [verify(ref).attrs["href"] for ref in root.select("img + a")]
    audio = verify(root.select_one(".music.download_link")).attrs["href"]

    token = verify(root.select_one('input[name="slides_data"]')).attrs["value"]

    base: list[AnyMedia] = [
        *[ImageMedia(url=image) for image in images],
        AudioMedia(url=audio),
    ]

    if not resolve_image_video:
        return base

    response = await client.post(
        "https://r.ssstik.top/index.sh",
        data={
            "slides_data": token,
        },
    )
    response.raise_for_status()

    final_url: str = verify(response.headers.get("Hx-Redirect"))

    res = VideoMedia(
        url=final_url,
        thumbnail_url=images[0] if images else None,
    )

    if not images_as_video:
        return [res, *base]

    return res


async def _find_links(
    client: AsyncClient,
    url: str,
    *,
    images_as_video: bool,
    resolve_image_video: bool,
    add_thumbnail: bool = False,
) -> VideoMedia | list[AnyMedia]:
    response = await client.get("https://ssstik.io/")
    response.raise_for_status()

    token = verify(TOKEN_REGEX.search(response.text)).group(1)

    response = await client.post(
        "https://ssstik.io/abc?url=dl",
        data={
            "id": url,
            "locale": "en",
            "tt": token,
        },
    )

    response.raise_for_status()
    verify(response.content)

    if 'id="slides_generate"' in response.text:
        return await _handle_images(
            client,
            response,
            images_as_video=images_as_video,
            resolve_image_video=resolve_image_video,
        )

    media = await _handle_video(client, response, add_thumbnail=add_thumbnail)
    return media if images_as_video else [media]


@overload
async def tiktok_resolve_links(
    url: str,
    *,
    images_as_video: Literal[True] = True,
    add_thumbnail: bool = False,
    resolve_image_video: bool = False,
    client: AsyncClient | None = None,
) -> VideoMedia:
    pass


@overload
async def tiktok_resolve_links(
    url: str,
    *,
    images_as_video: Literal[False],
    add_thumbnail: bool = False,
    resolve_image_video: bool = False,
    client: AsyncClient | None = None,
) -> list[AnyMedia]:
    pass


async def tiktok_resolve_links(
    url: str,
    *,
    images_as_video: bool = True,
    resolve_image_video: bool = False,
    add_thumbnail: bool = False,
    client: AsyncClient | None = None,
) -> VideoMedia | list[AnyMedia]:
    async with httpx_client(client) as client:
        return await _find_links(
            client,
            url,
            images_as_video=images_as_video,
            resolve_image_video=resolve_image_video,
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
