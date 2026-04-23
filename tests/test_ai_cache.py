import asyncio

import pytest

from app.ai.cache import TTLCache, cache_async_result, make_cache_key


@pytest.mark.asyncio
async def test_ttl_cache_set_get_expire():
    cache = TTLCache()
    await cache.set("k", "v", ttl_seconds=1)
    assert await cache.get("k") == "v"
    await asyncio.sleep(1.1)
    assert await cache.get("k") is None


@pytest.mark.asyncio
async def test_cache_decorator_hits():
    cache = TTLCache()
    calls = {"n": 0}

    @cache_async_result(cache, ttl_seconds=60, key_builder=lambda x: make_cache_key("fn", x))
    async def work(x: int) -> int:
        calls["n"] += 1
        return x * 2

    assert await work(2) == 4
    assert await work(2) == 4
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_ttl_cache_stats_and_invalidate_prefix():
    cache = TTLCache()
    await cache.set("site:a", "one", ttl_seconds=60)
    await cache.set("site:b", "two", ttl_seconds=60)
    assert await cache.get("site:a") == "one"
    assert await cache.get("missing") is None
    deleted = await cache.invalidate_prefix("site:")
    stats = await cache.stats()
    assert deleted == 2
    assert stats["hits"] >= 1
    assert stats["misses"] >= 1
