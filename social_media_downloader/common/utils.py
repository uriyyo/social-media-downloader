import re
from contextlib import AsyncExitStack, asynccontextmanager
from typing import AsyncIterator, TypeVar

from httpx import AsyncClient

from social_media_downloader.common.consts import DEFAULT_TIMEOUT

T = TypeVar("T")


class VerifyError(Exception):
    pass


def verify(obj: T | None, /, *, msg: str | None = None) -> T:
    if not obj:
        raise VerifyError(msg or f"Verification failed {obj!r}")

    return obj


@asynccontextmanager
async def httpx_client(client: AsyncClient | None = None) -> AsyncIterator[AsyncClient]:
    async with AsyncExitStack() as astack:
        if client is None:
            client = await astack.enter_async_context(AsyncClient(timeout=DEFAULT_TIMEOUT))

        client.follow_redirects = True
        yield client


def find_all_by_regex(pattern: re.Pattern[str], text: str) -> list[str]:
    return [g for m in pattern.finditer(text) if m and (g := m.group())]


__all__ = [
    "verify",
    "VerifyError",
    "httpx_client",
    "find_all_by_regex",
]
