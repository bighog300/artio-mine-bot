from unittest.mock import AsyncMock, patch

import pytest

from app.ai.openai_client import OpenAIClient
from app.ai.quality_assurance import AutomatedCrawler, QualityAssurance
from app.db import crud


def test_limit_config_for_testing_filters_invalid_urls() -> None:
    qa = QualityAssurance(OpenAIClient(api_key="test"))
    config = {
        "crawl_targets": [
            {"url": "https://example.com/events"},
            {"url": ""},
            {"url": "   "},
            {"url": "{{base_url}}"},
            {"url": "https://example.com/exhibitions"},
        ],
        "crawl_plan": {
            "phases": [
                {
                    "phase_name": "test",
                    "targets": [{"url": "https://example.com/legacy"}],
                }
            ]
        }
    }

    limited = qa._limit_config_for_testing(config)
    crawl_targets = limited["crawl_targets"]

    assert len(crawl_targets) == 2
    assert all(target["url"].startswith("https://example.com/") for target in crawl_targets)
    assert all(target["limit"] == 5 for target in crawl_targets)
    assert limited["crawl_plan"]["phases"] == []


def test_limit_config_for_testing_empties_phase_when_no_valid_targets() -> None:
    qa = QualityAssurance(OpenAIClient(api_key="test"))
    config = {
        "crawl_targets": [{"url": ""}, {"url": "{url}"}, {"url": "  "}],
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
    assert limited["crawl_targets"] == []
    assert limited["crawl_plan"]["phases"] == []


def test_limit_config_for_testing_preserves_extraction_rules() -> None:
    qa = QualityAssurance(OpenAIClient(api_key="test"))
    config = {
        "crawl_targets": [{"url": "https://example.com/artists"}],
        "crawl_plan": {"phases": [{"phase_name": "legacy"}]},
        "extraction_rules": {
            "artist_profile": {
                "identifiers": ["/artists/[^/]+/?$"],
                "css_selectors": {"title": "h1"},
            }
        },
    }

    limited = qa._limit_config_for_testing(config)

    assert "extraction_rules" in limited
    assert "artist_profile" in limited["extraction_rules"]
    assert limited["extraction_rules"]["artist_profile"] == config["extraction_rules"]["artist_profile"]
    assert "_QA_Test" in limited["extraction_rules"]
    assert limited["extraction_rules"]["_QA_Test"]["identifiers"] == ["^/__smart_test$", "/__smart_test"]
    assert limited["extraction_rules"]["_QA_Test"]["fields"]["title"]["selector"] == "title"
    assert limited["extraction_rules"]["_QA_Test"]["fields"]["heading"]["selector"] == "h1"
    assert "_QA_Test" not in config["extraction_rules"]


def test_limit_config_for_testing_forces_smart_test_target() -> None:
    qa = QualityAssurance(OpenAIClient(api_key="test"))
    config = {
        "crawl_targets": [{"url": "https://example.com/anything"}],
        "extraction_rules": {},
    }

    limited = qa._limit_config_for_testing(config, source_url="https://art.co.za")

    assert limited["crawl_targets"] == [{"url": "https://art.co.za/__smart_test", "limit": 1}]
    assert config["crawl_targets"] == [{"url": "https://example.com/anything"}]


def test_classify_by_url_prefers_specific_qa_rule_over_navigation() -> None:
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "_Navigation": {"identifiers": ["/.*"]},
                "_QA_Test": {
                    "identifiers": ["^/__smart_test$", "/__smart_test"],
                    "fields": {
                        "title": {"selector": "title"},
                        "heading": {"selector": "h1"},
                    },
                },
            }
        },
        db=None,
    )

    assert crawler._classify_by_url("https://art.co.za/__smart_test") == "_QA_Test"


def test_deterministic_extraction_for_qa_rule_returns_data() -> None:
    crawler = AutomatedCrawler(
        structure_map={
            "extraction_rules": {
                "_QA_Test": {
                    "identifiers": ["^/__smart_test$", "/__smart_test"],
                    "fields": {
                        "title": {"selector": "title"},
                        "heading": {"selector": "h1"},
                    },
                }
            }
        },
        db=None,
    )
    html = """
    <html>
      <head><title>Smart Test Page</title></head>
      <body><h1>Smart Test Page</h1></body>
    </html>
    """
    extracted = crawler._extract_deterministic(html, "_QA_Test", "https://art.co.za/__smart_test")

    assert extracted["data"]["title"] == "Smart Test Page"
    assert extracted["data"]["heading"] == "Smart Test Page"


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
