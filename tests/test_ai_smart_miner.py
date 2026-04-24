from unittest.mock import AsyncMock

import pytest

from app.ai.openai_client import OpenAIClient
from app.ai.smart_miner import SmartMiner
from app.db import crud


@pytest.mark.asyncio
async def test_smart_miner_happy_path(db_session) -> None:
    source = await crud.create_source(db_session, url="https://example.com", name="x")
    miner = SmartMiner(openai_client=OpenAIClient(api_key="test"))
    miner_runner = AsyncMock(return_value={"runtime_mode": "deterministic"})
    miner._run_deterministic_mine = miner_runner
    miner.site_analyzer.analyze = AsyncMock(return_value={"site_type": "art_gallery", "cms_platform": "custom", "entity_types": ["artist"], "url_patterns": {}, "confidence": 90, "notes": ""})
    miner.config_generator.generate = AsyncMock(return_value={"crawl_plan": {"phases": [{"phase_name": "artist"}]}, "extraction_rules": {"artist": {"identifiers": ["/artists/[^/]+/?$"], "css_selectors": {"title": "h1, h2"}}}})
    miner.qa.run = AsyncMock(return_value=({"crawl_plan": {"phases": [{"phase_name": "artist"}]}, "extraction_rules": {"artist": {"identifiers": ["/artists/[^/]+/?$"], "css_selectors": {"title": "h1, h2"}}}}, type("R", (), {"success_rate": 90.0})()))

    result = await miner.smart_mine(db_session, source.id, source.url)
    assert result.status == "completed"
    miner_runner.assert_awaited_once()
    refreshed = await crud.get_source(db_session, source.id)
    assert refreshed is not None and refreshed.structure_map is not None
