from unittest.mock import AsyncMock, patch

import pytest

from app.ai.openai_client import OpenAIClient
from app.ai.site_analyzer import SiteAnalyzer
from app.crawler.fetcher import FetchResult


@pytest.mark.asyncio
async def test_site_analyzer_returns_structured_payload() -> None:
    analyzer = SiteAnalyzer(OpenAIClient(api_key="test"))
    analyzer.openai_client.complete_json = AsyncMock(
        return_value={
            "site_type": "art_gallery",
            "cms_platform": "wordpress",
            "entity_types": ["artists", "events"],
            "url_patterns": {"artists": ["/artists/[^/]+/?$"]},
            "confidence": 92,
            "notes": "Looks like a gallery",
        }
    )
    with patch(
        "app.ai.site_analyzer.fetch",
        AsyncMock(
            return_value=FetchResult(
                url="https://example.com",
                final_url="https://example.com",
                html="<html><head><title>X</title></head><body><a href='/artists/jane'>Jane</a></body></html>",
                status_code=200,
                method="httpx",
            )
        ),
    ):
        result = await analyzer.analyze("https://example.com")

    assert result["site_type"] == "art_gallery"
    assert "artists" in result["entity_types"]
