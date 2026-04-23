from __future__ import annotations

import json

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.config_generator import ConfigGenerator
from app.ai.models import SmartMineResultModel
from app.ai.openai_client import OpenAIClient
from app.ai.quality_assurance import QualityAssurance
from app.ai.site_analyzer import SiteAnalyzer
from app.db import crud

logger = structlog.get_logger()


class SmartMiner:
    def __init__(self, openai_client: OpenAIClient | None = None) -> None:
        self.openai_client = openai_client or OpenAIClient()
        self.site_analyzer = SiteAnalyzer(self.openai_client)
        self.config_generator = ConfigGenerator(self.openai_client)
        self.qa = QualityAssurance(self.openai_client)

    async def smart_mine(self, db: AsyncSession, source_id: str, url: str) -> SmartMineResultModel:
        source = await crud.get_source(db, source_id)
        if source is None:
            raise ValueError(f"Source {source_id} not found")

        await crud.update_source(db, source_id, status="analyzing")
        analysis = await self.site_analyzer.analyze(url)

        await crud.update_source(db, source_id, status="generating_config")
        config = await self.config_generator.generate(url, analysis)

        await crud.update_source(db, source_id, status="testing")
        attempts = 0
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

    async def match_template(self, _url: str) -> None:
        return None
