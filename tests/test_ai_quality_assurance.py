from unittest.mock import AsyncMock, patch

import pytest

from app.ai.openai_client import OpenAIClient
from app.ai.quality_assurance import QualityAssurance
from app.db import crud


def test_limit_config_for_testing_filters_invalid_urls() -> None:
    qa = QualityAssurance(OpenAIClient(api_key="test"))
    config = {
        "crawl_plan": {
            "phases": [
                {
                    "phase_name": "test",
                    "targets": [
                        {"url": "https://example.com/events"},
                        {"url": ""},
                        {"url": "   "},
                        {"url": "{{base_url}}"},
                        {"url": "https://example.com/exhibitions"},
                    ],
                }
            ]
        }
    }

    limited = qa._limit_config_for_testing(config)
    phases = limited["crawl_plan"]["phases"]

    assert len(phases) == 1
    assert len(phases[0]["targets"]) == 2
    assert all(target["url"].startswith("https://example.com/") for target in phases[0]["targets"])
    assert all(target["limit"] == 5 for target in phases[0]["targets"])


def test_limit_config_for_testing_empties_phase_when_no_valid_targets() -> None:
    qa = QualityAssurance(OpenAIClient(api_key="test"))
    config = {
        "crawl_plan": {
            "phases": [
                {
                    "phase_name": "test",
                    "targets": [{"url": ""}, {"url": "{url}"}, {"url": "  "}],
                }
            ]
        }
    }

    limited = qa._limit_config_for_testing(config)
    assert limited["crawl_plan"]["phases"] == []


@pytest.mark.asyncio
async def test_quality_assurance_refines_when_low_success(db_session) -> None:
    source = await crud.create_source(db_session, url="https://example.com", name="main")
    qa = QualityAssurance(OpenAIClient(api_key="test"))
    qa._refine_config = AsyncMock(return_value={"crawl_plan": {"phases": [{"phase_name": "x"}]}, "extraction_rules": {"x": {"identifiers": ["/artists/[^/]+/?$"], "css_selectors": {"title": "h1"}}}})

    crawler_mock = AsyncMock()
    crawler_mock.execute_crawl_plan = AsyncMock(side_effect=[{"pages_crawled": 10, "extracted_deterministic": 2, "extracted_ai_fallback": 0}, {"pages_crawled": 10, "extracted_deterministic": 9, "extracted_ai_fallback": 0}])

    with patch("app.ai.quality_assurance.AutomatedCrawler", return_value=crawler_mock):
        _, report = await qa.run(
            db=db_session,
            source_id=source.id,
            source_url="https://example.com",
            config={"crawl_plan": {"phases": [{"phase_name": "x"}]}, "extraction_rules": {"x": {"identifiers": ["/artists/[^/]+/?$"], "css_selectors": {"title": "h1"}}}},
        )

    assert report.refined is True
    assert report.success_rate == 90.0
