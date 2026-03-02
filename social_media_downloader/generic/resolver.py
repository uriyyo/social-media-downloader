from typing import Any

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from httpx import AsyncClient

from ..common import ImageMedia, ResolverConfig, VideoMedia
from ..common.utils import httpx_client

_AES_KEY = b"qwertyuioplkjhgf"


def _encrypt_url(url: str) -> str:
    data = pad(url.encode(), AES.block_size)
    cipher = AES.new(_AES_KEY, AES.MODE_ECB)
    return cipher.encrypt(data).hex()


def _parse_media(data: dict[str, Any]) -> list[ImageMedia | VideoMedia]:
    result: list[ImageMedia | VideoMedia] = []

    for item in data.get("video", []):
        result.append(
            VideoMedia(
                url=item["video"],
                thumbnail_url=item.get("thumbnail"),
            ),
        )

    for item in data.get("image", []):
        if isinstance(item, str):
            result.append(ImageMedia(url=item))
        elif isinstance(item, dict):
            result.append(ImageMedia(url=item["image"]))

    return result


async def generic_resolve_links(
    url: str,
    *,
    config: ResolverConfig | None = None,
    client: AsyncClient | None = None,
) -> list[ImageMedia | VideoMedia]:
    async with httpx_client(client) as client:
        response = await client.get(
            "https://api.videodropper.app/allinone",
            headers={"url": _encrypt_url(url)},
        )
        response.raise_for_status()

        return _parse_media(response.json())


__all__ = [
    "generic_resolve_links",
]
