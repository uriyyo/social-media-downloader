from asyncio import sleep, timeout
from dataclasses import dataclass
from typing import AsyncIterator, Self

from .consts import DEFAULT_POOL, DEFAULT_TIMEOUT


@dataclass(frozen=True)
class ResolverConfig:
    timeout: float = DEFAULT_TIMEOUT
    pool: float = DEFAULT_POOL

    @classmethod
    def default(cls) -> Self:
        return cls()

    async def wait_ctx(self) -> AsyncIterator[Self]:
        async with timeout(self.timeout):
            while True:
                yield self
                await sleep(self.pool)


__all__ = [
    "ResolverConfig",
]
