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


def test_config_generator_fills_empty_identifiers_with_default() -> None:
    generator = ConfigGenerator(OpenAIClient(api_key="test"))
    config = {
        "extraction_rules": {
            "Artists": {"identifiers": [], "css_selectors": {"title": "h1.title"}},
        }
    }
    updated = generator._add_default_identifiers_if_empty(config)
    assert updated["extraction_rules"]["Artists"]["identifiers"] == ["/artist/[^/]+/?$"]


def test_user_prompt_includes_identifier_requirements() -> None:
    generator = ConfigGenerator(OpenAIClient(api_key="test"))
    prompt = generator._build_user_prompt(
        source_url="https://example.com",
        analysis={
            "site_type": "art_gallery",
            "cms_platform": "custom",
            "entity_types": ["artists"],
        },
        sample_pages={},
    )
    assert "NEVER use empty identifiers: []" in prompt
    assert "/artists/[^/]+/?$" in prompt


def test_normalize_extraction_rules_converts_list_to_dict() -> None:
    generator = ConfigGenerator(OpenAIClient(api_key="test"))
    config = {
        "extraction_rules": [
            {
                "entity_type": "Artists",
                "identifiers": ["/artists/[^/]+/?$"],
                "selectors": {"name": "h1.title", "bio": ".artist-bio"},
            },
            {
                "entity_type": "Exhibitions",
                "identifiers": ["/exhibitions/[^/]+/?$"],
                "css_selectors": {"title": "h1.title"},
            },
        ]
    }

    normalized = generator._normalize_extraction_rules(config)

    assert isinstance(normalized["extraction_rules"], dict)
    assert set(normalized["extraction_rules"].keys()) == {"Artists", "Exhibitions"}
    assert normalized["extraction_rules"]["Artists"]["css_selectors"] == {
        "name": "h1.title",
        "bio": ".artist-bio",
    }
    assert normalized["extraction_rules"]["Exhibitions"]["css_selectors"] == {"title": "h1.title"}


def test_normalize_extraction_rules_skips_missing_entity_type() -> None:
    generator = ConfigGenerator(OpenAIClient(api_key="test"))
    config = {
        "extraction_rules": [
            {"identifiers": ["/artists/[^/]+/?$"], "selectors": {"name": "h1.title"}},
            {"entity_type": "Artists", "identifiers": ["/artists/[^/]+/?$"], "selectors": {"name": "h1.title"}},
        ]
    }

    normalized = generator._normalize_extraction_rules(config)

    assert set(normalized["extraction_rules"].keys()) == {"Artists"}
