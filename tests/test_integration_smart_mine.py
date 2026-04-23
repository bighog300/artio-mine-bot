from unittest.mock import AsyncMock

import pytest

from app.ai.openai_client import OpenAIClient
from app.ai.smart_miner import SmartMiner
from app.db import crud


@pytest.mark.asyncio
async def test_integration_smart_mine_full_workflow(db_session) -> None:
    source = await crud.create_source(db_session, url="https://art.co.za", name="Artio Test")
    miner = SmartMiner(openai_client=OpenAIClient(api_key="test"))

    miner.site_analyzer.analyze = AsyncMock(
        return_value={
            "site_type": "art_gallery",
            "cms_platform": "wordpress",
            "entity_types": ["artist", "event"],
            "url_patterns": {"artist": ["/artists/[^/]+/?$"]},
            "confidence": 88,
            "notes": "integration mock",
        }
    )
    config = {
        "crawl_plan": {"phases": [{"phase_name": "artist_detail", "base_url": "https://art.co.za", "url_pattern": "/artists/[a-z0-9\\-]+/?", "pagination_type": "follow_links", "num_pages": 10}]},
        "extraction_rules": {"artist_detail": {"identifiers": ["/artists/[^/]+/?$"], "css_selectors": {"title": "h1.artist-name, h1"}}},
        "page_type_rules": {},
        "record_type_rules": {},
        "follow_rules": {},
        "asset_rules": {},
    }
    miner.config_generator.generate = AsyncMock(return_value=config)
    miner.qa.run = AsyncMock(return_value=(config, type("R", (), {"success_rate": 89.0})()))

    result = await miner.smart_mine(db_session, source.id, source.url)
    assert result.status == "completed"
    assert result.success_rate == 89.0
