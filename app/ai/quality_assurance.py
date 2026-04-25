from __future__ import annotations

import asyncio
import copy
import json
from typing import Any

import structlog
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.models import QualityReportModel
from app.ai.openai_client import OpenAIClient
from app.crawler.automated_crawler import AutomatedCrawler
from app.db import crud
from app.db.models import CrawlRun, Page, Record, Source

logger = structlog.get_logger()


class QualityAssurance:
    def __init__(self, openai_client: OpenAIClient) -> None:
        self.openai_client = openai_client

    def _limit_config_for_testing(self, config: dict[str, Any], *, source_url: str | None = None) -> dict[str, Any]:
        """Limit config for quick QA testing - only crawl a few pages from crawl_targets."""
        limited = copy.deepcopy(config)

        qa_target_url = None
        if source_url:
            qa_target_url = f"{source_url.rstrip('/')}/__smart_test"

        crawl_targets = limited.get("crawl_targets", [])

        if qa_target_url:
            limited["crawl_targets"] = [{"url": qa_target_url, "limit": 1}]
            logger.info("qa_forced_test_target", target_url=qa_target_url)
        elif not crawl_targets:
            logger.warning("qa_no_crawl_targets_found")
            return limited
        else:
            valid_targets: list[dict[str, Any]] = []
            removed_count = 0

            for target in crawl_targets:
                if not isinstance(target, dict):
                    continue

                url = str(target.get("url", ""))
                stripped_url = url.strip()

                if not stripped_url:
                    removed_count += 1
                    logger.warning("qa_skipped_empty_url_target")
                    continue

                if stripped_url in {"{{base_url}}", "{{url}}", "{url}", "{base_url}"}:
                    removed_count += 1
                    logger.warning("qa_skipped_placeholder_url", url=stripped_url)
                    continue

                valid_targets.append({"url": stripped_url, "limit": 5})

            if len(valid_targets) == 0:
                logger.error("qa_no_valid_targets_after_filtering", removed_count=removed_count)
                limited["crawl_targets"] = []
            else:
                limited["crawl_targets"] = valid_targets[:3]
                logger.info(
                    "qa_config_limited",
                    original_targets=len(crawl_targets),
                    valid_targets=len(valid_targets[:3]),
                    removed_empty=removed_count,
                )

        limited.setdefault("extraction_rules", {})
        limited["extraction_rules"]["_QA_Test"] = {
            "identifiers": ["^/__smart_test$", "/__smart_test"],
            "target_record_type": "artwork",
            "fields": {
                "title": {"selector": "title"},
                "heading": {"selector": "h1"},
            },
        }

        if "crawl_plan" in limited:
            limited["crawl_plan"]["phases"] = []
            logger.info("qa_cleared_phases_to_use_crawl_targets")

        return limited

    async def run(
        self,
        *,
        db: AsyncSession,
        source_id: str,
        source_url: str,
        config: dict[str, Any],
    ) -> tuple[dict[str, Any], QualityReportModel]:
        existing = await crud.get_source_by_url(db, f"{source_url.rstrip('/')}/__smart_test")
        if existing:
            temp_source = existing
            logger.info("qa_reusing_test_source", source_id=temp_source.id)
        else:
            temp_source = await crud.create_source(
                db,
                url=f"{source_url.rstrip('/')}/__smart_test",
                name="SmartMode QA",
            )
            logger.info("qa_created_test_source", source_id=temp_source.id)
        temp_source_id = temp_source.id

        try:
            limited_config = self._limit_config_for_testing(config, source_url=source_url)
            extraction_rules = limited_config.get("extraction_rules")
            logger.info(
                "qa_limited_config_rules",
                has_extraction_rules="extraction_rules" in limited_config,
                rule_names=list(extraction_rules.keys()) if isinstance(extraction_rules, dict) else [],
            )
            await crud.update_source(
                db,
                temp_source_id,
                structure_map=json.dumps(limited_config),
                status="testing",
            )
            logger.info("qa_starting_test_crawl", source_id=temp_source_id, pages_limit=5)

            crawler = AutomatedCrawler(structure_map=limited_config, db=db, ai_allowed=False)

            try:
                stats = await asyncio.wait_for(
                    crawler.execute_crawl_plan(temp_source_id),
                    timeout=60.0,
                )
            except asyncio.TimeoutError:
                logger.warning("qa_test_crawl_timeout", source_id=temp_source_id)
                return config, QualityReportModel(
                    pages_crawled=0,
                    records_created=0,
                    success_rate=0.0,
                    refined=False,
                    attempts=1,
                )

            pages_crawled = int(stats.get("pages_crawled", 0))
            records_created = int(stats.get("extracted_deterministic", 0)) + int(
                stats.get("extracted_ai_fallback", 0)
            )

            if pages_crawled == 0:
                success_rate = 0.0
            else:
                success_rate = round((records_created / pages_crawled) * 100, 2)

            logger.info(
                "qa_test_complete",
                pages_crawled=pages_crawled,
                records_created=records_created,
                success_rate=success_rate,
            )

            if success_rate >= 85:
                return config, QualityReportModel(
                    pages_crawled=pages_crawled,
                    records_created=records_created,
                    success_rate=success_rate,
                    refined=False,
                    attempts=1,
                )

            if pages_crawled == 0:
                logger.warning("qa_no_pages_crawled", source_id=source_id)
                return config, QualityReportModel(
                    pages_crawled=0,
                    records_created=0,
                    success_rate=0.0,
                    refined=False,
                    attempts=1,
                )

            logger.info("qa_attempting_refinement", current_success_rate=success_rate)
            refined = await self._refine_config(config=config, stats=stats)
            limited_refined = self._limit_config_for_testing(refined, source_url=source_url)
            crawler = AutomatedCrawler(structure_map=limited_refined, db=db, ai_allowed=False)

            try:
                second_stats = await asyncio.wait_for(
                    crawler.execute_crawl_plan(temp_source_id),
                    timeout=60.0,
                )
            except asyncio.TimeoutError:
                logger.warning("qa_refinement_timeout", source_id=temp_source_id)
                return config, QualityReportModel(
                    pages_crawled=pages_crawled,
                    records_created=records_created,
                    success_rate=success_rate,
                    refined=False,
                    attempts=2,
                )

            pages_crawled_2 = int(second_stats.get("pages_crawled", 0))
            records_created_2 = int(second_stats.get("extracted_deterministic", 0)) + int(
                second_stats.get("extracted_ai_fallback", 0)
            )
            if pages_crawled_2 == 0:
                success_rate_2 = 0.0
            else:
                success_rate_2 = round((records_created_2 / pages_crawled_2) * 100, 2)

            return refined, QualityReportModel(
                pages_crawled=pages_crawled_2,
                records_created=records_created_2,
                success_rate=success_rate_2,
                refined=True,
                attempts=2,
            )
        finally:
            await self._cleanup_temp_source(db=db, temp_source_id=temp_source_id)

    async def _cleanup_temp_source(self, *, db: AsyncSession, temp_source_id: str) -> None:
        try:
            await db.execute(delete(Record).where(Record.source_id == temp_source_id))
            await db.execute(delete(Page).where(Page.source_id == temp_source_id))
            await db.execute(delete(CrawlRun).where(CrawlRun.source_id == temp_source_id))
            await db.execute(delete(Source).where(Source.id == temp_source_id))
            await db.commit()
            logger.info("qa_cleaned_up_test_source", source_id=temp_source_id)
        except Exception as cleanup_error:
            await db.rollback()
            logger.warning(
                "qa_cleanup_failed",
                temp_source_id=temp_source_id,
                error=str(cleanup_error),
            )

    async def _refine_config(self, *, config: dict[str, Any], stats: dict[str, Any]) -> dict[str, Any]:
        prompt = "Refine mining config to improve success rate. Keep same top-level schema. Return JSON only."
        user_prompt = f"Config: {config}\nStats: {stats}"
        return await self.openai_client.complete_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            operation="config_refinement",
        )
