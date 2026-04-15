"""Analyze and reuse crawl structure for a source site."""

from string import ascii_lowercase
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from app.ai.client import OpenAIClient

logger = structlog.get_logger()

STRUCTURE_ANALYZER_PROMPT = """Analyze this website to find:
1. A-Z directory structure (where artist/item listings are)
2. Pagination patterns (letter-based, numbered, etc.)
3. Nested structure (detail pages under listings)
4. Data locations (where to find bio, contact, images, etc.)

Return ONLY JSON with keys: crawl_targets, mining_map, directory_structure, confidence."""


async def analyze_structure(url: str, html: str, ai_client: OpenAIClient) -> dict:
    """One-time AI structure analysis for crawl and extraction guidance."""
    nav_html = _extract_nav_html(html)[:2000]
    user_content = f"""Homepage: {url}

Navigation:
{nav_html}

HTML (first 3000 chars):
{html[:3000]}"""

    try:
        response = await ai_client.complete(
            system_prompt=STRUCTURE_ANALYZER_PROMPT,
            user_content=user_content,
            response_format={"type": "json_object"},
        )
        logger.info(
            "structure_analysis_complete",
            url=url,
            confidence=response.get("confidence", 0),
            targets=len(response.get("crawl_targets", [])),
        )
        return response
    except Exception as exc:
        logger.error("structure_analysis_failed", url=url, error=str(exc))
        raise


def _extract_nav_html(html: str) -> str:
    """Extract nav/header snippets to keep structure-analysis prompts compact."""
    soup = BeautifulSoup(html or "", "lxml")
    chunks = [str(tag)[:1000] for tag in soup.find_all(["nav", "header"]) if tag]
    return "\n".join(chunks)


def _generate_urls_from_pattern(base_url: str, pattern: str, limit: int = 100) -> list[str]:
    """Expand URL patterns like /artists/[letter] and /page/[number]."""
    if "[letter]" in pattern:
        return [urljoin(base_url, pattern.replace("[letter]", letter)) for letter in ascii_lowercase]
    if "[number]" in pattern or "[page]" in pattern:
        token = "[number]" if "[number]" in pattern else "[page]"
        return [urljoin(base_url, pattern.replace(token, str(i))) for i in range(1, limit + 1)]
    return [urljoin(base_url, pattern)]
