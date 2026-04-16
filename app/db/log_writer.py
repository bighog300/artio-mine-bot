import asyncio
import json
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models import Log

logger = structlog.get_logger()


class LogStreamManager:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[dict[str, Any]]] = set()

    def subscribe(self) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue[dict[str, Any]]) -> None:
        self._subscribers.discard(queue)

    async def publish(self, event: dict[str, Any]) -> None:
        dead: list[asyncio.Queue[dict[str, Any]]] = []
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                try:
                    _ = queue.get_nowait()
                    queue.put_nowait(event)
                except Exception:
                    dead.append(queue)
        for queue in dead:
            self._subscribers.discard(queue)


log_stream_manager = LogStreamManager()


class DatabaseLogProcessor:
    def __init__(
        self,
        service_name: str,
        session_factory: Callable[[], AsyncSession] = AsyncSessionLocal,
    ) -> None:
        self.service_name = service_name
        self.session_factory = session_factory
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        self._worker_task: asyncio.Task[None] | None = None

    async def start(self) -> None:
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker(), name=f"log-writer-{self.service_name}")

    async def stop(self) -> None:
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass

    async def _worker(self) -> None:
        while True:
            payload = await self._queue.get()
            try:
                async with self.session_factory() as session:
                    session.add(Log(**payload))
                    await session.commit()
                await log_stream_manager.publish(payload)
            except Exception:
                # Must never crash on log write failures.
                pass

    def __call__(self, _logger: Any, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        payload = self._normalize_payload(method_name, event_dict)
        try:
            self._queue.put_nowait(payload)
        except Exception:
            pass
        return event_dict

    def _normalize_payload(self, method_name: str, event_dict: dict[str, Any]) -> dict[str, Any]:
        level = str(event_dict.get("level", method_name)).lower()
        if level not in {"debug", "info", "warning", "error"}:
            level = "info"

        source_id = event_dict.get("source_id")
        message = str(event_dict.get("event", ""))
        timestamp_value = event_dict.get("timestamp")

        if isinstance(timestamp_value, datetime):
            timestamp = timestamp_value
        elif isinstance(timestamp_value, str):
            try:
                timestamp = datetime.fromisoformat(timestamp_value.replace("Z", "+00:00"))
            except Exception:
                timestamp = datetime.now(UTC)
        else:
            timestamp = datetime.now(UTC)

        context = {k: v for k, v in event_dict.items() if k not in {"event", "level", "timestamp", "source_id"}}
        return {
            "timestamp": timestamp,
            "level": level,
            "service": self.service_name,
            "source_id": source_id,
            "message": message,
            "context": json.dumps(context, default=str) if context else None,
        }


_processors: dict[str, DatabaseLogProcessor] = {}


def configure_structlog_for_service(service_name: str) -> DatabaseLogProcessor:
    processor = _processors.get(service_name)
    if processor is None:
        processor = DatabaseLogProcessor(service_name=service_name)
        _processors[service_name] = processor

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            processor,
            structlog.dev.ConsoleRenderer(),
        ]
    )
    return processor


async def list_logs(
    db: AsyncSession,
    *,
    level: str | None,
    service: str | None,
    source_id: str | None,
    search: str | None,
    job_id: str | None,
    worker_id: str | None,
    stage: str | None,
    date_from: datetime | None,
    date_to: datetime | None,
    skip: int,
    limit: int,
) -> tuple[list[Log], int]:
    stmt = select(Log)
    count_stmt = select(func.count(Log.id))

    filters = []
    if level:
        filters.append(Log.level == level)
    if service:
        filters.append(Log.service == service)
    if source_id:
        filters.append(Log.source_id == source_id)
    if search:
        filters.append(or_(Log.message.ilike(f"%{search}%"), Log.context.ilike(f"%{search}%")))
    if job_id:
        filters.append(Log.context.ilike(f"%{job_id}%"))
    if worker_id:
        filters.append(Log.context.ilike(f"%{worker_id}%"))
    if stage:
        filters.append(Log.context.ilike(f"%{stage}%"))
    if date_from:
        filters.append(Log.timestamp >= date_from)
    if date_to:
        filters.append(Log.timestamp <= date_to)

    for cond in filters:
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    stmt = stmt.order_by(Log.timestamp.desc()).offset(skip).limit(limit)

    items = list((await db.execute(stmt)).scalars().all())
    total = (await db.execute(count_stmt)).scalar_one()
    return items, total


async def delete_logs(db: AsyncSession, *, older_than_days: int, level: str | None) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=older_than_days)
    stmt = delete(Log).where(Log.timestamp < cutoff)
    if level:
        stmt = stmt.where(Log.level == level)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0
