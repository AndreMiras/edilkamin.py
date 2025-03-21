"""
Provides a decorator for writing functions that are both async- and sync-compatible.

The `@syncable` decorator allows defining a single `async def` function that can be
called from synchronous code as well. This is useful in libraries or scripts that
want to support both sync and async workflows without code duplication.

Internally, it dispatches to the async function if an event loop is running,
otherwise runs the async code using `anyio.run()`.

Example:

    @syncable
    async def fetch_data():
        ...

    # Sync usage
    data = fetch_data()

    # Async usage
    data = await fetch_data()
"""

import asyncio
from functools import wraps
from typing import Any, Awaitable, Callable, TypeVar, Union, cast

import anyio

T = TypeVar("T")
FuncT = TypeVar("FuncT", bound=Callable[..., Any])


class AsyncDispatch:
    def __init__(self, async_func: Callable[..., Awaitable[T]]):
        self.async_func = async_func

        @wraps(async_func)
        def sync_func(*args: Any, **kwargs: Any) -> T:
            return anyio.run(async_func, *args, **kwargs)

        self.sync_func = sync_func

    def __call__(self, *args: Any, **kwargs: Any) -> Union[Awaitable[T], T]:
        try:
            asyncio.get_running_loop()
            return self.async_func(*args, **kwargs)
        except RuntimeError:
            return self.sync_func(*args, **kwargs)


def syncable(async_func: FuncT) -> FuncT:
    return cast(FuncT, AsyncDispatch(async_func))
