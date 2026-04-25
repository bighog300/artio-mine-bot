"""Analyze and reuse crawl structure for a source site."""

from string import ascii_lowercase
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from app.ai.openai_client import OpenAIClient

logger = structlog.get_logger()

STRUCTURE_ANALYZER_PROMPT = """Analyze this website to find:
1. A-Z directory structure (where artist/item listings are)
2. Pagination patterns (letter-based, numbered, etc.)
3. Nested structure (detail pages under listings)
4. Data locations (where to find bio, contact, images, etc.)

Return ONLY JSON with this schema:
{
  "crawl_targets": ["/artists/[letter]", ...],
  "mining_map": {
    "artist_profile": {
      "url_pattern": "/artists/[name]",
      "expected_fields": ["name", "bio", "mediums", "contact"]
    }
  },
  "directory_structure": "...",
  "extraction_rules": {
    "artist_profile": {
      "identifiers": ["URL matches /artists/[letter]/[name]", "Page has biography section"],
      "extraction_method": "DETERMINISTIC",
      "css_selectors": {
        "name": "h1.artist-name",
        "bio": "div.biography",
        "mediums": "ul.mediums li",
        "contact": "div.contact-info"
      },
      "regex_patterns": {
        "birth_year": "Born (\\d{4})",
        "email": "Email: ([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,})"
      },
      "fallback": "Use GenAI only if CSS fails",
      "confidence": "HIGH - use simple extraction first",
      "ai_context_hint": "This is an artist profile page. Look for: name, bio, mediums, contact info, images",
      "expected_output_type": "artist_profile"
    }
  },
  "crawler_optimizations": {
    "recommended_batch_size": 10,
    "rate_limit_ms": 1000,
    "respect_robots_txt": true,
    "detect_captcha": true
  },
  "ai_fallback_rules": {
    "use_ai_when": [
      "CSS selector fails to extract data",
      "Page structure differs from expected pattern",
      "Extraction confidence would be < 80%"
    ],
    "ai_context_hint": "Use the page_type and expected fields from extraction_rules",
    "expected_output_type": "type-specific"
  },
  "confidence": 0
}

Rules:
- Provide CSS selectors and regex patterns for each page type in extraction_rules.
- Keep selector and regex values concise and practical for deterministic extraction.
- AI fallback is allowed only when deterministic confidence is below 80.
"""


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
