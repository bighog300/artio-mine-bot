from dataclasses import dataclass

import redis
from redis.exceptions import RedisError
from rq import Queue, Worker

from app.config import settings

_default_queue: Queue | None = None


class QueueUnavailableError(RuntimeError):
    """Raised when Redis/RQ infrastructure is not reachable."""


@dataclass
class QueueHealth:
    redis_ok: bool
    workers_available: bool
    worker_count: int


def get_default_queue() -> Queue:
    global _default_queue
    if _default_queue is None:
        try:
            redis_conn = redis.from_url(settings.redis_url)
            redis_conn.ping()
        except RedisError as exc:
            raise QueueUnavailableError(
                f"Redis unavailable for queue connection: {exc}"
            ) from exc
        _default_queue = Queue("default", connection=redis_conn)
    return _default_queue


def check_queue_health() -> QueueHealth:
    """Lightweight queue health signal for API diagnostics."""
    try:
        queue = get_default_queue()
        queue.connection.ping()
        workers = Worker.all(connection=queue.connection)
        worker_count = len(workers)
        return QueueHealth(
            redis_ok=True,
            workers_available=worker_count > 0,
            worker_count=worker_count,
        )
    except (RedisError, QueueUnavailableError):
        return QueueHealth(redis_ok=False, workers_available=False, worker_count=0)
