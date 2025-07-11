import re

from httpx import AsyncClient

from ..common import ImageMedia, ResolverConfig, VideoMedia, find_all_by_regex
from ..generic import generic_resolve_links

THREADS_LINK_REGEX = re.compile(
    r"(https://(www\.)?threads\.com)/(?:[@\w.\-]+/)?(?:p/[\w.-]+/)?",
    re.DOTALL | re.IGNORECASE,
)


def threads_all_links(text: str) -> list[str]:
    return find_all_by_regex(THREADS_LINK_REGEX, text)


async def threads_resolve_links(
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
    "threads_all_links",
    "threads_resolve_links",
]
