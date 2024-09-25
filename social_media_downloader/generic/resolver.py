from typing import Any, Iterable

from httpx import AsyncClient

from ..common import ImageMedia, ResolverConfig, VideoMedia
from ..common.utils import httpx_client, verify


async def _wait_for_job(
    client: AsyncClient,
    job_id: str,
    config: ResolverConfig,
) -> list[dict[str, Any]]:
    async for _ in config.wait_ctx():
        r = await client.get(f"https://app.publer.io/api/v1/job_status/{job_id}")

        if r.is_success and r.json().get("status") == "complete":
            return verify(r.json().get("payload"))

    raise TimeoutError("Failed to resolve media")


def _links_to_media(links: list[dict[str, Any]]) -> Iterable[ImageMedia | VideoMedia]:
    for link in links:
        if link["type"] == "video":
            yield VideoMedia(url=link["path"])
        else:
            yield ImageMedia(url=link["path"])


async def generic_resolve_links(
    url: str,
    *,
    config: ResolverConfig | None = None,
    client: AsyncClient | None = None,
) -> list[ImageMedia | VideoMedia]:
    config = config or ResolverConfig.default()

    async with httpx_client(client) as client:
        response = await client.post(
            "https://app.publer.io/hooks/media",
            json={"url": url, "iphone": True},
            headers={
                "Referer": "https://publer.io/",
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
                ),
            },
        )
        response.raise_for_status()

        job_id: str = verify(response.json().get("job_id"))

        links = await _wait_for_job(
            client,
            job_id=job_id,
            config=config,
        )

        return [*_links_to_media(links)]


__all__ = [
    "generic_resolve_links",
]
