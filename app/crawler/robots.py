import asyncio
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
import structlog

logger = structlog.get_logger()

_cache: dict[str, tuple[RobotFileParser | None, float]] = {}
CACHE_TTL = 3600  # 1 hour


def _domain(url: str) -> str:
    parsed = urlparse(url)
    return f"{parsed.scheme}://{parsed.netloc}"


class RobotsChecker:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def is_allowed(self, url: str) -> bool:
        domain = _domain(url)
        robots_url = f"{domain}/robots.txt"

        async with self._lock:
            cached = _cache.get(domain)
            if cached:
                parser, ts = cached
                if time.time() - ts < CACHE_TTL:
                    if parser is None:
                        return True
                    return parser.can_fetch("Artio-Miner", url) or parser.can_fetch("*", url)

        # Fetch robots.txt
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(robots_url)
                if resp.status_code == 200:
                    parser.parse(resp.text.splitlines())
                else:
                    # No robots.txt — allow everything
                    async with self._lock:
                        _cache[domain] = (None, time.time())
                    return True
        except Exception as exc:
            logger.warning("robots_fetch_error", url=robots_url, error=str(exc))
            async with self._lock:
                _cache[domain] = (None, time.time())
            return True

        async with self._lock:
            _cache[domain] = (parser, time.time())

        return parser.can_fetch("Artio-Miner", url) or parser.can_fetch("*", url)
