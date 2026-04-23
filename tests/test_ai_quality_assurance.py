from unittest.mock import AsyncMock, patch

import pytest

from app.ai.openai_client import OpenAIClient
from app.ai.quality_assurance import QualityAssurance
from app.db import crud


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
