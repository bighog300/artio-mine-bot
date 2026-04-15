from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import UTC, datetime


@dataclass
class RateLimitDecision:
    allowed: bool
    remaining: int
    reset_epoch: int


class InMemoryRateLimiter:
    def __init__(self, limit_per_minute: int = 100) -> None:
        self.limit_per_minute = limit_per_minute
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> RateLimitDecision:
        now = datetime.now(UTC).timestamp()
        window_start = now - 60
        bucket = self._buckets[key]
        while bucket and bucket[0] < window_start:
            bucket.popleft()

        if len(bucket) >= self.limit_per_minute:
            reset_epoch = int(bucket[0] + 60)
            return RateLimitDecision(
                allowed=False,
                remaining=0,
                reset_epoch=reset_epoch,
            )

        bucket.append(now)
        remaining = max(0, self.limit_per_minute - len(bucket))
        reset_epoch = int(bucket[0] + 60) if bucket else int(now + 60)
        return RateLimitDecision(
            allowed=True,
            remaining=remaining,
            reset_epoch=reset_epoch,
        )


rate_limiter = InMemoryRateLimiter(limit_per_minute=100)
