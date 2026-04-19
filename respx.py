from __future__ import annotations

from collections.abc import Awaitable, Callable
from contextlib import ContextDecorator
from functools import wraps
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class _Route:
    method: str
    url: str
    return_value: httpx.Response | None = None

    def mock(self, *, return_value: httpx.Response) -> "_Route":
        self.return_value = return_value
        return self


class _MockRouter(ContextDecorator):
    def __init__(self) -> None:
        self._routes: dict[tuple[str, str], _Route] = {}
        self._original_request: Callable[..., Awaitable[httpx.Response]] | None = None

    def __call__(self, fn: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(fn)
        async def wrapped(*args: Any, **kwargs: Any) -> Any:
            with self:
                return await fn(*args, **kwargs)

        return wrapped

    def __enter__(self) -> "_MockRouter":
        self._original_request = httpx.AsyncClient.request

        async def _mocked_request(client: httpx.AsyncClient, method: str, url: str, *args: Any, **kwargs: Any) -> httpx.Response:
            del client, args, kwargs
            method_upper = method.upper()
            key = (method_upper, str(url))
            route = self._routes.get(key)
            if route is None or route.return_value is None:
                raise AssertionError(f"No mocked response registered for {method_upper} {url}")
            original = route.return_value
            request = httpx.Request(method_upper, str(url))
            return httpx.Response(
                status_code=original.status_code,
                headers=original.headers,
                content=original.content,
                request=request,
            )

        httpx.AsyncClient.request = _mocked_request
        return self

    def __exit__(self, *exc_info: Any) -> None:
        if self._original_request is not None:
            httpx.AsyncClient.request = self._original_request
        self._routes.clear()
        self._original_request = None

    def route(self, method: str, url: str) -> _Route:
        route = _Route(method=method.upper(), url=str(url))
        self._routes[(route.method, route.url)] = route
        return route


mock = _MockRouter()


def get(url: str) -> _Route:
    return mock.route("GET", url)


def head(url: str) -> _Route:
    return mock.route("HEAD", url)
