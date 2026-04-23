from __future__ import annotations

import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.cache import TTLCache, cache_async_result, make_cache_key
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


class SmartMiner:
    def __init__(self, openai_client: OpenAIClient | None = None, template_library: TemplateLibrary | None = None) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.site_analyzer = SiteAnalyzer(self.openai_client)
        self.config_generator = ConfigGenerator(self.openai_client)
        self.qa = QualityAssurance(self.openai_client)
        self.template_library = template_library or TemplateLibrary()
        self._analysis_cache = TTLCache()
        self._template_match_cache = TTLCache()

    @cache_async_result(
        cache=TTLCache(),
        ttl_seconds=ANALYSIS_CACHE_TTL_SECONDS,
        key_builder=lambda self, url: make_cache_key("site_analysis", url),
    )
    async def _analyze_site_cached(self, url: str) -> dict:
        return await self.site_analyzer.analyze(url)

    @cache_async_result(
        cache=TTLCache(),
        ttl_seconds=TEMPLATE_MATCH_CACHE_TTL_SECONDS,
        key_builder=lambda self, analysis: make_cache_key("template_match", analysis),
    )
    async def _match_template_cached(self, analysis: dict) -> dict | None:
        match = self.template_library.match_template(analysis)
        if not match:
            return None
        return {"template_id": match.template_id, "score": match.score}

    async def smart_mine(self, db: AsyncSession, source_id: str, url: str) -> SmartMineResultModel:
        source = await crud.get_source(db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        await crud.update_source(db, source_id, status="analyzing")
        analysis = await self._analyze_site_cached(url)

        template_info = await self._match_template_cached(analysis)
        config: dict
        if template_info:
            template_id = template_info["template_id"]
            logger.info("template_selected", source_id=source_id, template_id=template_id, score=template_info["score"])
            config = self.template_library.apply_template(template_id, url)
            self.template_library.increment_usage(template_id)
        else:
            await crud.update_source(db, source_id, status="generating_config")
            config = await self.config_generator.generate(url, analysis)

        await crud.update_source(db, source_id, status="testing")
        attempts = 0
        report = type("R", (), {"success_rate": 0.0})()
        for attempt in range(1, 3):
            attempts = attempt
            tested_config, report = await self.qa.run(db=db, source_id=source_id, source_url=url, config=config)
            config = tested_config
            if report.success_rate >= 85:
                break

        status = "completed" if report.success_rate >= 85 else "needs_human_review"
        await crud.update_source(db, source_id, status="mining", structure_map=json.dumps(config))

        logger.info(
            "smart_mine_complete",
            source_id=source_id,
            success_rate=report.success_rate,
            attempts=attempts,
            status=status,
            usage=self.openai_client.get_usage_totals(),
        )
        return SmartMineResultModel(
            source_id=source_id,
            status=status,
            success_rate=report.success_rate,
            attempts=attempts,
            analysis=dict(analysis),
            cost_summary=self.openai_client.get_usage_totals(),
            config=config,
            message=None if status == "completed" else "Escalate to human for mapping review.",
        )

    async def match_template(self, url: str) -> dict | None:
        analysis = await self._analyze_site_cached(url)
        return await self._match_template_cached(analysis)
