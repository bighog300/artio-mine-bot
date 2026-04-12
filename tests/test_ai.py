import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.classifier import ClassifyResult, classify_page
from app.ai.confidence import score_record
from app.ai.extractors.artist import ArtistExtractor
from app.ai.extractors.event import EventExtractor

ARTIST_JSONLD_HTML = """
<html>
<head><title>Eric Duplan — Artist</title></head>
<body>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Person", "name": "Eric Duplan"}
</script>
<main>
<h1>Eric Duplan</h1>
<p>Abstract artist from Cape Town.</p>
<img src="https://example.com/eric.jpg" alt="Eric Duplan portrait">
</main>
</body>
</html>
"""

EVENT_JSONLD_HTML = """
<html>
<head><title>Gallery Opening Night</title></head>
<body>
<script type="application/ld+json">
{"@context": "https://schema.org", "@type": "Event", "name": "Gallery Opening Night",
 "startDate": "2026-04-15", "location": {"name": "Gallery XYZ"}}
</script>
<main><h1>Gallery Opening Night</h1></main>
</body>
</html>
"""

UNKNOWN_HTML = """
<html><body><p>Login to your account</p><form><input type="password"></form></body></html>
"""


@pytest.fixture
def mock_ai_client():
    client = MagicMock()
    client.complete = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_classify_artist_profile_jsonld(mock_ai_client):
    result = await classify_page(
        url="https://example.com/artists/eric-duplan",
        html=ARTIST_JSONLD_HTML,
        ai_client=mock_ai_client,
    )
    assert result.page_type == "artist_profile"
    assert result.confidence >= 90
    # AI should NOT be called since JSON-LD matched
    mock_ai_client.complete.assert_not_called()


@pytest.mark.asyncio
async def test_classify_event_jsonld(mock_ai_client):
    result = await classify_page(
        url="https://example.com/events/opening",
        html=EVENT_JSONLD_HTML,
        ai_client=mock_ai_client,
    )
    assert result.page_type == "event_detail"
    assert result.confidence >= 90
    mock_ai_client.complete.assert_not_called()


@pytest.mark.asyncio
async def test_classify_unknown(mock_ai_client):
    mock_ai_client.complete.return_value = {
        "page_type": "unknown",
        "confidence": 10,
        "reasoning": "Login page, not art content",
    }
    result = await classify_page(
        url="https://example.com/login",
        html=UNKNOWN_HTML,
        ai_client=mock_ai_client,
    )
    assert result.page_type == "unknown"


@pytest.mark.asyncio
async def test_extract_artist(mock_ai_client):
    mock_ai_client.complete.return_value = {
        "name": "Eric Duplan",
        "bio": "Abstract painter from Cape Town.",
        "nationality": "South African",
        "birth_year": 1962,
        "mediums": ["oil painting", "watercolour"],
        "website_url": "https://www.ericduplan.com",
        "instagram_url": None,
        "email": None,
        "collections": ["UNISA", "Old Mutual"],
        "avatar_url": "https://example.com/eric.jpg",
        "image_urls": [],
    }
    extractor = ArtistExtractor(mock_ai_client)
    result = await extractor.extract(
        url="https://example.com/artists/eric-duplan",
        html=ARTIST_JSONLD_HTML,
    )
    assert result["name"] == "Eric Duplan"
    assert "oil painting" in result["mediums"]
    assert "UNISA" in result["collections"]


@pytest.mark.asyncio
async def test_extract_event(mock_ai_client):
    mock_ai_client.complete.return_value = {
        "title": "Gallery Opening Night",
        "description": "Join us for the opening.",
        "start_date": "2026-04-15",
        "end_date": "2026-04-15",
        "venue_name": "Gallery XYZ",
        "venue_address": "123 Art Street",
        "artist_names": ["Jane Smith"],
        "ticket_url": None,
        "is_free": True,
        "price_text": None,
        "image_urls": ["https://example.com/poster.jpg"],
    }
    extractor = EventExtractor(mock_ai_client)
    result = await extractor.extract(
        url="https://example.com/events/opening",
        html=EVENT_JSONLD_HTML,
    )
    assert result["title"] == "Gallery Opening Night"
    assert result["start_date"] == "2026-04-15"
    assert "Jane Smith" in result["artist_names"]


def test_confidence_high():
    data = {
        "name": "Eric Duplan",
        "bio": "Abstract painter.",
        "mediums": ["oil"],
        "collections": [],
        "artist_names": [],
        "_ai_confidence": 85,  # +5 high AI confidence
        "_jsonld_source": True,  # +10 JSON-LD source
    }
    images = ["https://example.com/img.jpg"]
    score, band, reasons = score_record("artist", data, images)
    # name(+20) + bio(+15) + image(+15) + jsonld(+10) + ai_confidence(+5) = 65...
    # Add venue_name to get +10 = 75
    data["venue_name"] = "Gallery XYZ"
    score, band, reasons = score_record("artist", data, images)
    assert score >= 70
    assert band == "HIGH"
    assert len(reasons) >= 2


def test_confidence_low():
    data = {"title": "Unknown Event"}
    images: list[str] = []
    score, band, reasons = score_record("event", data, images)
    assert score < 40
    assert band == "LOW"
