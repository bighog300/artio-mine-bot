import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any


@dataclass
class CacheEntry:
    value: Any
    expires_at: datetime


class TTLCache:
    def __init__(self, default_ttl_seconds: int = 60) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._store: dict[str, CacheEntry] = {}
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < datetime.now(UTC):
                self._store.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl_seconds
        async with self._lock:
            self._store[key] = CacheEntry(
                value=value,
                expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
            )


response_cache = TTLCache(default_ttl_seconds=120)
