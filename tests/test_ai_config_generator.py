from unittest.mock import AsyncMock

import pytest

from app.ai.config_generator import ConfigGenerator
from app.ai.openai_client import OpenAIClient


@pytest.mark.asyncio
async def test_config_generator_validate_rejects_broad_identifier() -> None:
    generator = ConfigGenerator(OpenAIClient(api_key="test"))
    with pytest.raises(ValueError, match="too broad"):
        generator.validate_config(
            {
                "crawl_plan": {"phases": [{"phase_name": "a"}]},
                "extraction_rules": {"artist": {"identifiers": ["/"], "css_selectors": {"title": "h1"}}},
            }
        )


@pytest.mark.asyncio
async def test_config_generator_generate_success() -> None:
    generator = ConfigGenerator(OpenAIClient(api_key="test"))
    generator._fetch_sample_pages = AsyncMock(return_value={})
    generator.openai_client.complete_json = AsyncMock(
        return_value={
            "crawl_plan": {"phases": [{"phase_name": "artist", "base_url": "https://example.com", "url_pattern": "/artists/[^/]+/?$", "pagination_type": "follow_links", "num_pages": 10}]},
            "extraction_rules": {"artist": {"identifiers": ["/artists/[^/]+/?$"], "css_selectors": {"title": "h1.title, h1, h2"}}},
            "page_type_rules": {},
            "record_type_rules": {},
            "follow_rules": {},
            "asset_rules": {},
        }
    )
    config = await generator.generate(
        "https://example.com",
        {
            "site_type": "art_gallery",
            "cms_platform": "custom",
            "entity_types": ["artist"],
            "url_patterns": {},
            "confidence": 90,
            "notes": "",
        },
    )
    assert "crawl_plan" in config
