import asyncio
from dataclasses import dataclass, field
from typing import Any

import httpx
import structlog

from app.config import settings

logger = structlog.get_logger()

BATCH_SIZE = 50


@dataclass
class ExportResult:
    exported: list[str] = field(default_factory=list)
    failed: list[dict[str, Any]] = field(default_factory=list)


class ArtioClient:
    def __init__(self) -> None:
        self.api_url = settings.artio_api_url
        self.api_key = settings.artio_api_key

    async def push_records(self, records: list[dict[str, Any]]) -> ExportResult:
        """Push records to Artio in batches of 50."""
        result = ExportResult()

        if not self.api_url or not self.api_key:
            logger.warning("artio_not_configured")
            for r in records:
                result.failed.append({"id": r.get("id"), "error": "Artio API not configured"})
            return result

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=30, headers=headers) as client:
            # Process in batches
            for i in range(0, len(records), BATCH_SIZE):
                batch = records[i : i + BATCH_SIZE]
                await self._push_batch(client, batch, result)

        return result

    async def _push_batch(
        self,
        client: httpx.AsyncClient,
        batch: list[dict[str, Any]],
        result: ExportResult,
    ) -> None:
        url = f"{self.api_url}/api/feed/ingest"
        try:
            resp = await client.post(url, json=batch)
            if resp.status_code < 300:
                for record in batch:
                    result.exported.append(record["id"])
            elif 400 <= resp.status_code < 500:
                # Client error — mark each as failed
                for record in batch:
                    result.failed.append(
                        {
                            "id": record.get("id"),
                            "error": f"{resp.status_code} {resp.text[:200]}",
                        }
                    )
            else:
                # Server error — retry once
                await asyncio.sleep(5)
                try:
                    resp2 = await client.post(url, json=batch)
                    if resp2.status_code < 300:
                        for record in batch:
                            result.exported.append(record["id"])
                    else:
                        for record in batch:
                            result.failed.append(
                                {"id": record.get("id"), "error": f"{resp2.status_code}"}
                            )
                except Exception as exc:
                    for record in batch:
                        result.failed.append({"id": record.get("id"), "error": str(exc)})

        except Exception as exc:
            logger.error("artio_push_error", error=str(exc))
            for record in batch:
                result.failed.append({"id": record.get("id"), "error": str(exc)})
