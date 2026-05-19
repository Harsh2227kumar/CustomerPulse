import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

T = TypeVar("T")


async def with_retries(operation: Callable[[], Awaitable[T]], max_retries: int) -> T:
    last_error: Exception | None = None
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception as exc:
            last_error = exc
            if attempt >= max_retries:
                break
            await asyncio.sleep(0.5 * (attempt + 1))
    assert last_error is not None
    raise last_error
