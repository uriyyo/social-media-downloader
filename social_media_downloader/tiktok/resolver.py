import asyncio
import json
import logging
import re
from functools import wraps
from typing import Any, Awaitable, Callable, Literal, ParamSpec, TypeAlias, TypeVar, overload
from urllib.parse import parse_qs, urlparse, urlunparse

from bs4 import BeautifulSoup
from httpx import AsyncClient, Response

from ..common import AudioMedia, ImageMedia, RawMedia, VideoMedia, images_to_video, verify
from ..common.utils import find_all_by_regex, httpx_client
from ..generic.resolver import generic_resolve_links

logger = logging.getLogger(__name__)

AnyMedia: TypeAlias = VideoMedia | ImageMedia | AudioMedia | RawMedia

TOKEN_REGEX = re.compile(r"s_tt\s*=\s*'(.*?)'")

TIKTOK_LINK_REGEX = re.compile(
    r"https://(vm|vt|www)\.tiktok\.com/[@\w+/-]+/?",
    re.DOTALL | re.IGNORECASE,
)

FINAL_URL_REGEX = re.compile(r"^https://r\d+\.ssstik\.top/.*")

UNIVERSAL_DATA_REGEX = re.compile(
    r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.+?)</script>',
    re.DOTALL,
)

_MOBILE_USER_AGENT = (
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1"
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

    await asyncio.sleep(1)
    response = await client.post(
        "https://r.ssstik.top/index.sh",
        data={
            "slides_data": token,
        },
    )
    response.raise_for_status()

    final_url: str = verify(response.headers.get("Hx-Redirect"))

    assert FINAL_URL_REGEX.match(final_url), f"Invalid final URL {final_url}"

    res = VideoMedia(
        url=final_url,
        thumbnail_url=images[0] if images else None,
    )

    if not images_as_video:
        return [res, *base]

    return res


async def _find_links_old(
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
    if images_as_video:
        return media
    return [media]


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

    return str(verify(response.json().get("thumbnail_url")))


P = ParamSpec("P")
R = TypeVar("R")


def _retry_call(
    func: Callable[P, Awaitable[R]],
    retries: int,
    interval: float,
) -> Callable[P, Awaitable[R]]:
    @wraps(func)
    async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        for _ in range(retries):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.warning("Failed to call %s: %s", func, e)
                await asyncio.sleep(interval)

        return await func(*args, **kwargs)

    return wrapper


async def _find_links(
    client: AsyncClient,
    url: str,
    *,
    images_as_video: bool = False,
    add_thumbnail: bool = False,
) -> VideoMedia | list[AnyMedia]:
    medias = await _retry_call(
        generic_resolve_links,
        retries=3,
        interval=1,
    )(url, client=client)

    videos = [m for m in medias if isinstance(m, VideoMedia)]
    non_videos = [m for m in medias if not isinstance(m, VideoMedia)]

    verify(len(videos) >= 1, msg="Expected more than zero video media")
    (video, *_) = videos

    if add_thumbnail:
        if non_videos:
            video.thumbnail_url = non_videos[0].url
        else:
            video.thumbnail_url = await _resolve_thumbnail(url, client)

    if images_as_video:
        return video

    return [video, *non_videos]


async def _find_links_facade(
    client: AsyncClient,
    url: str,
    *,
    images_as_video: bool = True,
    add_thumbnail: bool = False,
) -> VideoMedia | list[AnyMedia]:
    try:
        r = await _retry_call(_find_links_old, retries=3, interval=1)(
            client,
            url,
            resolve_image_video=True,
            images_as_video=images_as_video,
            add_thumbnail=add_thumbnail,
        )

        assert r, "Failed to resolve media"
    except Exception:
        logger.exception("Failed to resolve media")
    else:
        return r

    return await _find_links(
        client,
        url,
        images_as_video=images_as_video,
        add_thumbnail=add_thumbnail,
    )


async def _resolve_item_id(client: AsyncClient, url: str) -> str:
    response = await client.head(url, follow_redirects=True)
    match = re.search(r"/(?:video|photo)/(\d+)", str(response.url))
    return verify(match, msg=f"Could not extract item ID from {response.url}").group(1)


def _extract_video_data(text: str) -> dict[str, Any] | None:
    match = re.search(r'"videoData"\s*:\s*(\{)', text)
    if not match:
        return None

    start = match.start(1)
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                result: dict[str, Any] = json.loads(text[start : i + 1])
                return result

    return None


async def _find_links_webapp(
    client: AsyncClient,
    url: str,
    *,
    images_as_video: bool = True,
    add_thumbnail: bool = False,
) -> VideoMedia | RawMedia | list[AnyMedia]:
    response = await client.get(url, headers={"User-Agent": _MOBILE_USER_AGENT})
    response.raise_for_status()

    match = verify(
        UNIVERSAL_DATA_REGEX.search(response.text),
        msg="universal data script not found (WAF challenge or layout change)",
    )
    universal = json.loads(match.group(1))
    item = verify(
        universal.get("__DEFAULT_SCOPE__", {})
        .get("webapp.reflow.video.detail", {})
        .get("itemInfo", {})
        .get("itemStruct"),
        msg="itemStruct not found in universal data",
    )

    cookie_header = "; ".join(f"{name}={value}" for name, value in client.cookies.items())
    cdn_headers = {
        "Referer": "https://www.tiktok.com/",
        "User-Agent": _MOBILE_USER_AGENT,
        "Cookie": cookie_header,
    }

    image_post = item.get("imagePost")
    if image_post:
        images = [
            ImageMedia(url=img["imageURL"]["urlList"][0], headers=cdn_headers)
            for img in image_post.get("images", [])
            if img.get("imageURL", {}).get("urlList")
        ]
        music_url = item.get("music", {}).get("playUrl")
        audio = AudioMedia(url=music_url, headers=cdn_headers) if music_url else None

        if images_as_video and images and audio:
            video_bytes = await images_to_video(images, audio, client=client)
            return RawMedia(content=video_bytes, content_type="video/mp4")

        result: list[AnyMedia] = [*images]
        if audio:
            result.append(audio)
        return result

    video = item.get("video", {})
    play_addr = verify(video.get("playAddr"), msg="playAddr missing from itemStruct")
    cover = (video.get("cover") or video.get("originCover")) if add_thumbnail else None

    return VideoMedia(
        url=play_addr,
        thumbnail_url=cover,
        headers=cdn_headers,
    )


async def _find_links_tikwm(
    client: AsyncClient,
    url: str,
    *,
    images_as_video: bool = True,
    add_thumbnail: bool = False,
) -> VideoMedia | RawMedia | list[AnyMedia]:
    response = await client.post(
        "https://www.tikwm.com/api/",
        data={"url": url, "hd": "1"},
    )
    response.raise_for_status()

    payload = response.json()
    verify(payload.get("code") == 0, msg=f"tikwm error: {payload.get('msg')}")
    data = verify(payload.get("data"))

    cover = data.get("cover") or data.get("origin_cover") if add_thumbnail else None
    images = data.get("images") or []

    if not images:
        video_url = verify(
            data.get("hdplay") or data.get("play"),
            msg="tikwm response missing video URL",
        )
        return VideoMedia(
            url=video_url,
            thumbnail_url=cover,
        )

    image_medias = [ImageMedia(url=img) for img in images]
    music_url = (data.get("music_info") or {}).get("play") or data.get("music")
    audio = AudioMedia(url=music_url) if music_url else None

    if images_as_video and image_medias and audio:
        video_bytes = await images_to_video(image_medias, audio, client=client)
        return RawMedia(content=video_bytes, content_type="video/mp4")

    result: list[AnyMedia] = [*image_medias]
    if audio:
        result.append(audio)
    return result


async def _find_links_fast(
    client: AsyncClient,
    url: str,
    *,
    images_as_video: bool = True,
    add_thumbnail: bool = False,
) -> VideoMedia | RawMedia | list[AnyMedia]:
    headers = {
        "Referer": "https://www.tiktok.com/",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
        ),
    }

    item_id = await _resolve_item_id(client, url)

    response = await client.get(
        f"https://www.tiktok.com/embed/{item_id}",
        headers=headers,
    )
    response.raise_for_status()

    video_data = _extract_video_data(response.text)
    if video_data:
        item = video_data.get("itemInfos", {})
        video = item.get("video", {})
        video_urls = video.get("urls", [])
        covers = item.get("covers", [])
        cover = covers[0] if covers and add_thumbnail else None

        if video_urls:
            return VideoMedia(
                url=video_urls[0],
                thumbnail_url=cover,
                headers=headers,
            )

        image_post = video_data.get("imagePostInfo", {})
        display_images = image_post.get("displayImages", [])
        music = video_data.get("musicInfos", {})
        music_urls = music.get("playUrl", [])

        if display_images:
            image_medias = [ImageMedia(url=img["urlList"][0]) for img in display_images if img.get("urlList")]
            audio = AudioMedia(url=music_urls[0]) if music_urls else None

            if images_as_video and image_medias and audio:
                video_bytes = await images_to_video(image_medias, audio, client=client)
                return RawMedia(content=video_bytes, content_type="video/mp4")

            result: list[AnyMedia] = [*image_medias]
            if audio:
                result.append(audio)
            return result

    return await _find_links_facade(
        client,
        url,
        images_as_video=images_as_video,
        add_thumbnail=add_thumbnail,
    )


async def _resolve_comment_video_link(
    url: str,
    client: AsyncClient,
) -> str:
    response = await client.head(url, follow_redirects=True)
    final = urlparse(str(response.url))

    if "share_comment_id" not in parse_qs(final.query):
        return url

    return urlunparse((final.scheme, final.netloc, final.path, "", "", ""))


@overload
async def tiktok_resolve_links(
    url: str,
    *,
    images_as_video: Literal[True] = True,
    add_thumbnail: bool = False,
    client: AsyncClient | None = None,
) -> VideoMedia | RawMedia:
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
) -> VideoMedia | RawMedia | list[AnyMedia]:
    async with httpx_client(client) as client:
        url = await _resolve_comment_video_link(url, client)

        try:
            return await _retry_call(_find_links_webapp, retries=2, interval=1)(
                client,
                url,
                images_as_video=images_as_video,
                add_thumbnail=add_thumbnail,
            )
        except Exception:
            logger.exception("Failed to resolve via webapp, falling back to tikwm")

        try:
            return await _retry_call(_find_links_tikwm, retries=2, interval=1)(
                client,
                url,
                images_as_video=images_as_video,
                add_thumbnail=add_thumbnail,
            )
        except Exception:
            logger.exception("Failed to resolve via tikwm, falling back to embed")

        return await _find_links_fast(
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


async def tiktok_is_comment(
    url: str,
    *,
    client: AsyncClient | None = None,
) -> bool:
    async with httpx_client(client) as client:
        response = await client.head(url, follow_redirects=True)
        query = parse_qs(urlparse(str(response.url)).query)
        return "share_comment_id" in query


__all__ = [
    "tiktok_all_links",
    "tiktok_is_comment",
    "tiktok_is_video",
    "tiktok_resolve_links",
]
