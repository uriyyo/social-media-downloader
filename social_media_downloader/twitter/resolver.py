import re

from httpx import AsyncClient

from ..common import ImageMedia, ResolverConfig, VideoMedia, find_all_by_regex
from ..generic import generic_resolve_links

TWITTER_LINK_REGEX = re.compile(
    r"https://(x|twitter).com/[\w/]+",
    re.DOTALL | re.IGNORECASE,
)


def twitter_all_links(text: str) -> list[str]:
    return find_all_by_regex(TWITTER_LINK_REGEX, text)


async def twitter_resolve_links(
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
    "twitter_all_links",
    "twitter_resolve_links",
]
