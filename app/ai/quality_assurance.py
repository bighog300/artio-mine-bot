from __future__ import annotations

import json
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import QualityReportModel
from app.ai.openai_client import OpenAIClient
from app.crawler.automated_crawler import AutomatedCrawler
from app.db import crud

logger = structlog.get_logger()


class QualityAssurance:
    def __init__(self, openai_client: OpenAIClient) -> None:
        self.openai_client = openai_client

    async def run(
        self,
        *,
        db: AsyncSession,
        source_id: str,
        source_url: str,
        config: dict[str, Any],
    ) -> tuple[dict[str, Any], QualityReportModel]:
        temp_source = await crud.create_source(db, url=f"{source_url.rstrip('/')}/__smart_test", name="SmartMode QA")
        try:
            await crud.update_source(db, temp_source.id, structure_map=json.dumps(config), status="testing")
            crawler = AutomatedCrawler(structure_map=config, db=db, ai_allowed=False)
            stats = await crawler.execute_crawl_plan(temp_source.id)
            pages_crawled = int(stats.get("pages_crawled", 0))
            records_created = int(stats.get("extracted_deterministic", 0)) + int(stats.get("extracted_ai_fallback", 0))
            success_rate = round((records_created / max(pages_crawled, 1)) * 100, 2)

            if success_rate >= 85:
                return config, QualityReportModel(
                    pages_crawled=pages_crawled,
                    records_created=records_created,
                    success_rate=success_rate,
                    refined=False,
                    attempts=1,
                )

            refined = await self._refine_config(config=config, stats=stats)
            crawler = AutomatedCrawler(structure_map=refined, db=db, ai_allowed=False)
            second_stats = await crawler.execute_crawl_plan(temp_source.id)
            pages_crawled_2 = int(second_stats.get("pages_crawled", 0))
            records_created_2 = int(second_stats.get("extracted_deterministic", 0)) + int(second_stats.get("extracted_ai_fallback", 0))
            success_rate_2 = round((records_created_2 / max(pages_crawled_2, 1)) * 100, 2)
            return refined, QualityReportModel(
                pages_crawled=pages_crawled_2,
                records_created=records_created_2,
                success_rate=success_rate_2,
                refined=True,
                attempts=2,
            )
        finally:
            await crud.delete_source(db, temp_source.id)

    async def _refine_config(self, *, config: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
        prompt = "Refine mining config to improve success rate. Keep same top-level schema. Return JSON only."
        user_prompt = f"Config: {config}\nStats: {stats}"
        return await self.openai_client.complete_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            operation="config_refinement",
        )
