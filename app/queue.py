import redis
from rq import Queue

from app.config import settings

_default_queue: Queue | None = None


def get_default_queue() -> Queue:
    global _default_queue
    if _default_queue is None:
        redis_conn = redis.from_url(settings.redis_url)
        _default_queue = Queue("default", connection=redis_conn)
    return _default_queue
