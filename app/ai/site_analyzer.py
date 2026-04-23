from __future__ import annotations

from typing import TypedDict
from urllib.parse import urljoin, urlparse

import structlog
from bs4 import BeautifulSoup

from app.ai.openai_client import OpenAIClient
from app.config import settings
from app.crawler.fetcher import fetch

logger = structlog.get_logger()


class SiteAnalysis(TypedDict):
    site_type: str
    cms_platform: str
    entity_types: list[str]
    url_patterns: dict[str, list[str]]
    confidence: int
    notes: str


class SiteAnalyzer:
    def __init__(self, openai_client: OpenAIClient) -> None:
        self.openai_client = openai_client

    async def analyze(self, url: str) -> SiteAnalysis:
        homepage = await fetch(url)
        if not homepage.html:
            raise ValueError(f"Could not fetch site homepage: {url}")

        soup = BeautifulSoup(homepage.html, "lxml")
        links = [
            urljoin(homepage.final_url, node.get("href", "").strip())
            for node in soup.select("a[href]")
            if node.get("href")
        ]
        same_domain_links = [
            link for link in links if urlparse(link).netloc == urlparse(homepage.final_url).netloc
        ]

        prompt = (
            "Analyze this website homepage and navigation links to identify site type, CMS,"
            " entity types and URL patterns. Return JSON with keys:"
            " site_type, cms_platform, entity_types, url_patterns, confidence, notes."
        )
        user_prompt = (
            f"URL: {homepage.final_url}\n"
            f"Title: {soup.title.text.strip() if soup.title and soup.title.text else ''}\n"
            f"Meta generator: {(soup.select_one('meta[name=generator]') or {}).get('content', '') if soup.select_one('meta[name=generator]') else ''}\n"
            f"Top links: {same_domain_links[:30]}\n"
            f"HTML snippet:\n{homepage.html[:6000]}"
        )

        result = await self.openai_client.complete_json(
            system_prompt=prompt,
            user_prompt=user_prompt,
            model=settings.openai_model_analysis,
            temperature=0,
        )

        site_analysis: SiteAnalysis = {
            "site_type": str(result.get("site_type", "unknown")),
            "cms_platform": str(result.get("cms_platform", "unknown")),
            "entity_types": [str(x) for x in result.get("entity_types", []) if isinstance(x, str)],
            "url_patterns": {
                str(k): [str(v) for v in vals if isinstance(v, str)]
                for k, vals in result.get("url_patterns", {}).items()
                if isinstance(vals, list)
            },
            "confidence": int(result.get("confidence", 0) or 0),
            "notes": str(result.get("notes", "")),
        }
        logger.info("site_analysis_complete", url=url, site_type=site_analysis["site_type"])
        return site_analysis
