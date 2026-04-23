from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from functools import wraps
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar("T")


@dataclass
class CacheEntry:
    value: Any
    expires_at: float


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at <= time.time():
                self._store.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        async with self._lock:
            self._store[key] = CacheEntry(value=value, expires_at=time.time() + ttl_seconds)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def cleanup_expired(self) -> int:
        now = time.time()
        async with self._lock:
            keys = [k for k, v in self._store.items() if v.expires_at <= now]
            for key in keys:
                self._store.pop(key, None)
            return len(keys)


def make_cache_key(prefix: str, *parts: Any) -> str:
    raw_parts = [prefix]
    for part in parts:
        if isinstance(part, (dict, list, tuple)):
            raw_parts.append(json.dumps(part, sort_keys=True))
        else:
            raw_parts.append(str(part))
    payload = "::".join(raw_parts)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def cache_async_result(
    cache: TTLCache,
    *,
    ttl_seconds: int,
    key_builder: Callable[..., str] | None = None,
) -> Callable[[Callable[..., Awaitable[T]]], Callable[..., Awaitable[T]]]:
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            cache_key = key_builder(*args, **kwargs) if key_builder else make_cache_key(func.__name__, args, kwargs)
            cached = await cache.get(cache_key)
            if cached is not None:
                logger.info("cache_hit", key=cache_key, function=func.__name__)
                return cached

            logger.info("cache_miss", key=cache_key, function=func.__name__)
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl_seconds)
            return result

        return wrapper

    return decorator
