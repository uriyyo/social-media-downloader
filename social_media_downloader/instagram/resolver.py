import re

from httpx import AsyncClient

from ..common import ImageMedia, ResolverConfig, VideoMedia, find_all_by_regex
from ..generic import generic_resolve_links

INSTAGRAM_LINK_REGEX = re.compile(
    r"https://(www\.)?instagram\.com/(p|reel)/([\w-]+)",
    re.DOTALL | re.IGNORECASE,
)


def instagram_all_links(text: str) -> list[str]:
    return find_all_by_regex(INSTAGRAM_LINK_REGEX, text)


async def instagram_resolve_links(
    url: str,
    *,
    config: ResolverConfig | None = None,
    client: AsyncClient | None = None,
) -> list[ImageMedia | VideoMedia]:
    return await generic_resolve_links(
        url,
        config=config,
        client=client,
    )


__all__ = [
    "instagram_all_links",
    "instagram_resolve_links",
]
