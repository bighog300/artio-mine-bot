from __future__ import annotations

import copy
import json
from dataclasses import dataclass

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import TTLCache, make_cache_key
from app.ai.config_generator import ConfigGenerator
from app.ai.models import SmartMineResultModel
from app.ai.openai_client import OpenAIClient
from app.ai.quality_assurance import QualityAssurance
from app.ai.site_analyzer import SiteAnalyzer
from app.ai.templates import TemplateLibrary
from app.db import crud

logger = structlog.get_logger()
ANALYSIS_CACHE_TTL_SECONDS = 24 * 60 * 60
TEMPLATE_MATCH_CACHE_TTL_SECONDS = 60 * 60
POPULAR_SITE_WARMUPS = ("https://www.artsy.net", "https://www.saatchiart.com", "https://www.tate.org.uk")
COST_ALERT_THRESHOLD_USD = 0.15


@dataclass
class CostAlert:
    url: str
    source_id: str
    cost_per_url_usd: float


class SmartMiner:
    def __init__(self, openai_client: OpenAIClient | None = None, template_library: TemplateLibrary | None = None) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.site_analyzer = SiteAnalyzer(self.openai_client)
        self.config_generator = ConfigGenerator(self.openai_client)
        self.qa = QualityAssurance(self.openai_client)
        self.template_library = template_library or TemplateLibrary()
        self._analysis_cache = TTLCache()
        self._template_match_cache = TTLCache()
        self._url_fingerprint: dict[str, str] = {}
        self._cost_alerts: list[CostAlert] = []

    async def _analyze_site_cached(self, url: str) -> dict:
        key = make_cache_key("site_analysis", url)
        cached = await self._analysis_cache.get(key)
        if cached is not None:
            return cached
        result = await self.site_analyzer.analyze(url)
        await self._analysis_cache.set(key, result, ANALYSIS_CACHE_TTL_SECONDS)
        return result

    async def _match_template_cached(self, analysis: dict) -> dict | None:
        key = make_cache_key("template_match", analysis)
        cached = await self._template_match_cache.get(key)
        if cached is not None:
            return cached
        match = self.template_library.match_template(analysis)
        if not match:
            await self._template_match_cache.set(key, None, TEMPLATE_MATCH_CACHE_TTL_SECONDS)
            return None
        payload = {"template_id": match.template_id, "score": match.score}
        await self._template_match_cache.set(key, payload, TEMPLATE_MATCH_CACHE_TTL_SECONDS)
        return payload

    async def warm_cache(self) -> dict[str, float]:
        warmed = 0
        for url in POPULAR_SITE_WARMUPS:
            try:
                await self._analyze_site_cached(url)
                warmed += 1
            except (RuntimeError, ValueError, OSError):
                logger.warning("smart_cache_warm_failed", url=url)
        return {"warmed_urls": float(warmed), "requested_urls": float(len(POPULAR_SITE_WARMUPS))}

    async def invalidate_for_site_change(self, url: str, fingerprint: str) -> bool:
        previous = self._url_fingerprint.get(url)
        self._url_fingerprint[url] = fingerprint
        if previous is None or previous == fingerprint:
            return False
        deleted = await self._analysis_cache.invalidate_prefix("site_analysis:")
        await self._template_match_cache.invalidate_prefix("template_match:")
        logger.info("smart_cache_invalidate", url=url, deleted=deleted, reason="site_changed")
        return True

    async def cache_stats(self) -> dict[str, dict[str, float]]:
        return {
            "analysis_cache": await self._analysis_cache.stats(),
            "template_match_cache": await self._template_match_cache.stats(),
        }

    def recent_cost_alerts(self) -> list[dict[str, str | float]]:
        return [
            {"url": alert.url, "source_id": alert.source_id, "cost_per_url_usd": round(alert.cost_per_url_usd, 6)}
            for alert in self._cost_alerts[-25:]
        ]

    async def _run_deterministic_mine(self, db: AsyncSession, source_id: str) -> dict:
        from app.pipeline.runner import PipelineRunner

        return await PipelineRunner(db, self.openai_client).run_deterministic_mine(source_id)

    async def smart_mine(self, db: AsyncSession, source_id: str, url: str) -> SmartMineResultModel:
        logger.info("smart_mine_start", source_id=source_id, url=url)
        source = await crud.get_source(db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        start_cost = self.openai_client.get_usage_totals()["estimated_cost_usd"]
        await self.invalidate_for_site_change(url, fingerprint=url.rstrip("/").lower())
        await crud.update_source(db, source_id, status="analyzing")
        logger.info("smart_mine_analyzing", source_id=source_id)
        analysis = await self._analyze_site_cached(url)
        logger.info("smart_mine_analyzed", source_id=source_id, site_type=analysis.get("site_type"))

        template_info = await self._match_template_cached(analysis)
        config: dict
        if template_info:
            template_id = template_info["template_id"]
            logger.info("template_selected", source_id=source_id, template_id=template_id, score=template_info["score"])
            config = self.template_library.apply_template(template_id, url)
            self.template_library.increment_usage(template_id)
        else:
            logger.info("smart_mine_generating_config", source_id=source_id)
            await crud.update_source(db, source_id, status="generating_config")
            config = await self.config_generator.generate(url, analysis)
        logger.info("smart_mine_config_ready", source_id=source_id)

        await crud.update_source(db, source_id, status="testing")
        attempts = 0
        report = type("R", (), {"success_rate": 0.0})()
        logger.info("smart_mine_testing_config", source_id=source_id)
        for attempt in range(1, 3):
            attempts = attempt
            tested_config, report = await self.qa.run(db=db, source_id=source_id, source_url=url, config=config)
            config = tested_config
            if report.success_rate >= 85:
                break
        config = self._ensure_production_crawl_targets(config, source_url=url)

        status = "completed" if report.success_rate >= 85 else "needs_human_review"
        await crud.update_source(db, source_id, status="mining", structure_map=json.dumps(config))
        logger.info("smart_mine_qa_complete", source_id=source_id, success_rate=report.success_rate, attempts=attempts)
        production_pages = 0
        production_records = 0
        status_reason: str | None = None
        if status == "completed":
            logger.info("smart_mine_starting_crawl", source_id=source_id)
            await crud.update_source(db, source_id, status="mining")
            result = await self._run_deterministic_mine(db, source_id)
            production_pages = int(result.get("pages_count", 0))
            production_records = int(result.get("records_count", 0))
            logger.info(
                "smart_mine_crawl_complete",
                source_id=source_id,
                pages=production_pages,
                records=production_records,
            )
            if production_pages == 0 or production_records == 0:
                status = "needs_human_review"
                status_reason = (
                    f"Production crawl insufficient results (pages_crawled={production_pages}, "
                    f"records_created={production_records})."
                )
                logger.warning(
                    "smart_mine_production_results_insufficient",
                    source_id=source_id,
                    pages_crawled=production_pages,
                    records_created=production_records,
                )

        logger.info(
            "smart_mine_complete",
            source_id=source_id,
            success_rate=report.success_rate,
            attempts=attempts,
            status=status,
            production_pages_crawled=production_pages,
            production_records_created=production_records,
            status_reason=status_reason,
            usage=self.openai_client.get_usage_totals(),
        )
        total_cost_delta = self.openai_client.get_usage_totals()["estimated_cost_usd"] - start_cost
        if total_cost_delta > COST_ALERT_THRESHOLD_USD:
            self._cost_alerts.append(CostAlert(url=url, source_id=source_id, cost_per_url_usd=total_cost_delta))
            logger.warning("smart_mine_cost_alert", source_id=source_id, url=url, cost_usd=round(total_cost_delta, 6))
        return SmartMineResultModel(
            source_id=source_id,
            status=status,
            success_rate=report.success_rate,
            attempts=attempts,
            analysis=dict(analysis),
            cost_summary=self.openai_client.get_usage_totals(),
            config=config,
            message=None if status == "completed" else (status_reason or "Escalate to human for mapping review."),
        )

    async def match_template(self, url: str) -> dict | None:
        analysis = await self._analyze_site_cached(url)
        return await self._match_template_cached(analysis)

    def _ensure_production_crawl_targets(self, config: dict, *, source_url: str) -> dict:
        ensured = copy.deepcopy(config)
        normalized_urls: list[str] = []
        seen: set[str] = set()

        def _add(url: str | None) -> None:
            if not isinstance(url, str):
                return
            candidate = url.strip()
            if not candidate or candidate in seen:
                return
            seen.add(candidate)
            normalized_urls.append(candidate)

        crawl_targets = ensured.get("crawl_targets", [])
        if isinstance(crawl_targets, list):
            for target in crawl_targets:
                if isinstance(target, dict):
                    _add(target.get("url"))
                elif isinstance(target, str):
                    _add(target)

        crawl_plan = ensured.get("crawl_plan", {})
        phases = crawl_plan.get("phases", []) if isinstance(crawl_plan, dict) else []
        if isinstance(phases, list):
            for phase in phases:
                if not isinstance(phase, dict):
                    continue
                phase_targets = phase.get("targets")
                if isinstance(phase_targets, list):
                    for target in phase_targets:
                        if isinstance(target, dict):
                            _add(target.get("url"))
                        elif isinstance(target, str):
                            _add(target)
                phase_urls = phase.get("urls")
                if isinstance(phase_urls, list):
                    for phase_url in phase_urls:
                        _add(phase_url if isinstance(phase_url, str) else None)

        if not normalized_urls:
            _add(source_url)

        ensured["crawl_targets"] = [{"url": candidate} for candidate in normalized_urls]
        logger.info("smart_mine_persisting_production_crawl_targets", crawl_targets=ensured["crawl_targets"])
        return ensured
