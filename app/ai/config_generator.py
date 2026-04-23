from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from app.ai.site_analyzer import SiteAnalysis
from app.ai.openai_client import OpenAIClient
from app.config import settings
from app.crawler.fetcher import fetch
from app.db import crud

logger = structlog.get_logger()

FORBIDDEN_IDENTIFIERS = {"/", ".", "/."}
FORBIDDEN_SELECTOR_SINGLE = {"p", "div", "a"}


class ConfigGenerator:
    def __init__(self, openai_client: OpenAIClient) -> None:
        self.openai_client = openai_client

    async def generate(self, source_url: str, analysis: SiteAnalysis) -> dict[str, Any]:
        sample_pages = await self._fetch_sample_pages(source_url, analysis)
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(source_url, analysis, sample_pages)
        config = await self.openai_client.complete_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=settings.openai_model_config,
            temperature=0.1,
        )
        self.validate_config(config)
        validation = crud.validate_mapping_template(config)
        if not validation["ok"]:
            raise ValueError(f"Generated config failed schema validation: {validation['errors']}")
        return config

    async def _fetch_sample_pages(self, source_url: str, analysis: SiteAnalysis) -> dict[str, str]:
        homepage = await fetch(source_url)
        if not homepage.html:
            return {}
        soup = BeautifulSoup(homepage.html, "lxml")
        result: dict[str, str] = {}
        links = [urljoin(homepage.final_url, a.get("href", "").strip()) for a in soup.select("a[href]")]

        for entity in analysis.get("entity_types", []):
            matching = [
                link for link in links if entity.rstrip("s") in link.lower() or entity.lower() in link.lower()
            ]
            if matching:
                page = await fetch(matching[0])
                if page.html:
                    result[entity] = page.html[:5000]
        return result

    def validate_config(self, config: dict[str, Any]) -> None:
        extraction_rules = config.get("extraction_rules", {})
        if not isinstance(extraction_rules, dict) or not extraction_rules:
            raise ValueError("Config must include non-empty extraction_rules.")

        for page_type, rule in extraction_rules.items():
            identifiers = rule.get("identifiers", [])
            if not isinstance(identifiers, list) or not identifiers:
                raise ValueError(f"extraction_rules.{page_type}.identifiers must be non-empty list")
            for identifier in identifiers:
                ident = str(identifier).strip()
                if ident in FORBIDDEN_IDENTIFIERS or len(ident) < 3:
                    raise ValueError(f"Identifier '{ident}' is too broad or too short")

            selectors = rule.get("css_selectors", {})
            if not isinstance(selectors, dict):
                raise ValueError(f"extraction_rules.{page_type}.css_selectors must be object")
            for field, selector in selectors.items():
                sel = str(selector).strip()
                if not sel:
                    raise ValueError(f"Selector for {page_type}.{field} cannot be empty")
                if sel in FORBIDDEN_SELECTOR_SINGLE:
                    raise ValueError(f"Selector '{sel}' is overly broad")
                if re.fullmatch(r"[a-zA-Z]+", sel) and sel.lower() in FORBIDDEN_SELECTOR_SINGLE:
                    raise ValueError(f"Selector '{sel}' is overly broad")

    def _build_system_prompt(self) -> str:
        return (
            "Generate a strict JSON mining config for art websites. "
            "Output keys: crawl_plan, extraction_rules, page_type_rules, record_type_rules, "
            "follow_rules, asset_rules. Avoid broad identifiers (/ . /.) and generic selectors."
        )

    def _build_user_prompt(
        self,
        source_url: str,
        analysis: SiteAnalysis,
        sample_pages: dict[str, str],
    ) -> str:
        return (
            f"Source URL: {source_url}\n"
            f"Site analysis: {analysis}\n"
            f"Sample pages by entity: {list(sample_pages.keys())}\n"
            "Return robust fallback selectors like 'h1.title, h1, h2'. "
            "Set crawl_plan.phases as non-empty list."
        )
