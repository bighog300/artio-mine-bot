import json
import re
from dataclasses import dataclass

import structlog
from bs4 import BeautifulSoup

from app.ai.client import AIExtractionError, OpenAIClient, PAGE_CLASSIFIER_PROMPT

logger = structlog.get_logger()

# URL patterns for rule-based classification
URL_PATTERNS = [
    (r"/artists/[a-zA-Z]/?$", "artist_directory_letter"),
    (r"/[^/]+/about\.php/?$", "artist_biography"),
    (r"/[^/]+/exhibitions\.php/?$", "artist_exhibitions"),
    (r"/[^/]+/articles\.php/?$", "artist_articles"),
    (r"/[^/]+/press(?:-reviews)?\.php/?$", "artist_press"),
    (r"/[^/]+/memories\.php/?$", "artist_memories"),
    (r"/artist[s]?/[^/]+/?$", "artist_profile"),
    (r"/artist[s]?/?$", "artist_directory"),
    (r"/event[s]?/[^/]+/?$", "event_detail"),
    (r"/event[s]?/?$", "event_listing"),
    (r"/what[s-]?[-_]?on/?", "event_listing"),
    (r"/exhibition[s]?/[^/]+/?$", "exhibition_detail"),
    (r"/exhibition[s]?/?$", "exhibition_listing"),
    (r"/show[s]?/[^/]+/?$", "exhibition_detail"),
    (r"/venue[s]?/?$", "venue_profile"),
    (r"/gallery/?$", "venue_profile"),
    (r"/artwork[s]?/[^/]+/?$", "artwork_detail"),
    (r"/artwork[s]?/?$", "artwork_listing"),
    (r"/shop/?$", "artwork_listing"),
    (r"/portfolio/?$", "artwork_listing"),
]

# JSON-LD type to page_type mapping
JSONLD_TYPE_MAP = {
    "Person": "artist_profile",
    "Artist": "artist_profile",
    "Event": "event_detail",
    "ExhibitionEvent": "event_detail",
    "MusicEvent": "event_detail",
    "Exhibition": "exhibition_detail",
    "LocalBusiness": "venue_profile",
    "Museum": "venue_profile",
    "ArtGallery": "venue_profile",
    "VisualArtwork": "artwork_detail",
    "Product": "artwork_detail",
}


@dataclass
class ClassifyResult:
    page_type: str
    confidence: int
    reasoning: str


def _extract_jsonld_type(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    for script in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(script.string or "")
            if isinstance(data, list):
                data = data[0]
            schema_type = data.get("@type", "")
            if isinstance(schema_type, list):
                schema_type = schema_type[0] if schema_type else ""
            if schema_type in JSONLD_TYPE_MAP:
                return JSONLD_TYPE_MAP[schema_type]
        except Exception:
            continue
    return None


def _classify_by_url(url: str) -> str | None:
    for pattern, page_type in URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return page_type
    return None


def _classify_by_content(html: str) -> str | None:
    soup = BeautifulSoup(html, "lxml")
    text = soup.get_text(separator=" ", strip=True).lower()
    if "artist names starting with" in text:
        return "artist_directory_letter"

    hub_labels = {"biography", "exhibitions", "articles", "press reviews", "memories"}
    nav_link_labels = {
        a.get_text(strip=True).lower()
        for a in soup.find_all("a", href=True)
        if a.get_text(strip=True)
    }
    if hub_labels.issubset(nav_link_labels):
        return "artist_profile_hub"
    return None


def _count_date_patterns(html: str) -> int:
    """Count date-like patterns in text as a signal for event/exhibition pages."""
    text = BeautifulSoup(html, "lxml").get_text()
    date_patterns = [
        r"\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b",
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{4}-\d{2}-\d{2}\b",
    ]
    count = 0
    for p in date_patterns:
        count += len(re.findall(p, text, re.IGNORECASE))
    return count


def _preprocess_for_classification(html: str) -> str:
    """Strip noise and truncate HTML for AI classification."""
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.find_all(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # Also include any remaining HTML structure
    remaining = str(soup)[:6000]
    return remaining


async def classify_page(url: str, html: str, ai_client: OpenAIClient) -> ClassifyResult:
    # Rule 1: JSON-LD @type
    jsonld_type = _extract_jsonld_type(html)
    if jsonld_type:
        logger.info("classify_jsonld", url=url, page_type=jsonld_type)
        return ClassifyResult(
            page_type=jsonld_type,
            confidence=95,
            reasoning=f"JSON-LD @type matched: {jsonld_type}",
        )

    # Rule 2: URL pattern matching
    url_type = _classify_by_url(url)
    if url_type:
        logger.info("classify_url_pattern", url=url, page_type=url_type)
        return ClassifyResult(
            page_type=url_type,
            confidence=75,
            reasoning=f"URL pattern matched: {url_type}",
        )

    # Rule 3: Content pattern matching
    content_type = _classify_by_content(html)
    if content_type:
        logger.info("classify_content_pattern", url=url, page_type=content_type)
        return ClassifyResult(
            page_type=content_type,
            confidence=80,
            reasoning=f"Content pattern matched: {content_type}",
        )

    # Rule 4: AI classification
    try:
        preprocessed = _preprocess_for_classification(html)
        response = await ai_client.complete(
            system_prompt=PAGE_CLASSIFIER_PROMPT,
            user_content=f"URL: {url}\n\nHTML:\n{preprocessed}",
            response_format={"type": "json_object"},
        )
        return ClassifyResult(
            page_type=response.get("page_type", "unknown"),
            confidence=response.get("confidence", 0),
            reasoning=response.get("reasoning", ""),
        )
    except AIExtractionError as exc:
        logger.warning("classify_ai_failed", url=url, error=str(exc))
        return ClassifyResult(
            page_type="unknown",
            confidence=0,
            reasoning=f"AI classification failed: {exc}",
        )
