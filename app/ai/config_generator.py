from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

import structlog
from bs4 import BeautifulSoup

from app.ai.site_analyzer import SiteAnalysis
from app.ai.openai_client import OpenAIClient
from app.ai.prompt_utils import compact_prompt, smart_html_preview
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
            operation="config_generation",
        )
        config = self._normalize_extraction_rules(config)
        config = self._add_default_identifiers_if_empty(config)
        config = self._fix_empty_urls_in_crawl_plan(config, source_url)
        config = self._validate_and_clean_crawl_targets(config)
        config = self._ensure_crawl_plan_has_targets(config, source_url)
        config = self._flatten_phases_to_crawl_targets(config)
        config = self._ensure_homepage_navigation_rule(config)
        self.validate_config(config)
        validation = crud.validate_mapping_template(config)
        if not validation["ok"]:
            raise ValueError(f"Generated config failed schema validation: {validation['errors']}")
        return config

    def _normalize_extraction_rules(self, config: dict[str, Any]) -> dict[str, Any]:
        """Convert extraction_rules from list to dict format if needed.

        OpenAI sometimes returns extraction_rules as a list of objects with entity_type,
        but we need a dict keyed by entity_type.
        """
        extraction_rules = config.get("extraction_rules", {})

        if isinstance(extraction_rules, dict):
            return config

        if isinstance(extraction_rules, list):
            normalized: dict[str, Any] = {}
            for rule in extraction_rules:
                if not isinstance(rule, dict):
                    continue

                entity_type = rule.get("entity_type")
                if not entity_type:
                    logger.warning(
                        "extraction_rule_missing_entity_type",
                        rule_keys=list(rule.keys()),
                    )
                    continue

                normalized_rule: dict[str, Any] = {}

                if "identifiers" in rule:
                    normalized_rule["identifiers"] = rule["identifiers"]

                if "selectors" in rule:
                    normalized_rule["css_selectors"] = rule["selectors"]
                elif "css_selectors" in rule:
                    normalized_rule["css_selectors"] = rule["css_selectors"]

                for key, value in rule.items():
                    if key not in ["entity_type", "selectors", "identifiers", "css_selectors"]:
                        normalized_rule[key] = value

                normalized[str(entity_type)] = normalized_rule

            config["extraction_rules"] = normalized
            logger.info(
                "normalized_extraction_rules_list_to_dict",
                original_count=len(extraction_rules),
                normalized_count=len(normalized),
                entity_types=list(normalized.keys()),
            )

        return config

    def _add_default_identifiers_if_empty(self, config: dict[str, Any]) -> dict[str, Any]:
        """Add default identifiers when model output leaves them empty."""
        extraction_rules = config.get("extraction_rules", {})
        if not isinstance(extraction_rules, dict):
            return config

        for page_type, rule in extraction_rules.items():
            if not isinstance(rule, dict):
                continue
            identifiers = rule.get("identifiers", [])
            if not isinstance(identifiers, list) or len(identifiers) == 0:
                normalized_page_type = str(page_type).lower().replace(" ", "_")
                singular_page_type = normalized_page_type.rstrip("s")
                default_pattern = f"/{singular_page_type}/[^/]+/?$"
                rule["identifiers"] = [default_pattern]
                logger.warning(
                    "openai_empty_identifiers_fixed",
                    page_type=page_type,
                    default_pattern=default_pattern,
                )
        return config

    def _fix_empty_urls_in_crawl_plan(self, config: dict[str, Any], source_url: str) -> dict[str, Any]:
        """Remove or fix empty URLs in crawl plan targets."""
        crawl_plan = config.get("crawl_plan", {})
        if not isinstance(crawl_plan, dict):
            return config

        phases = crawl_plan.get("phases", [])
        if not isinstance(phases, list):
            return config

        fixed_count = 0
        removed_count = 0

        for phase in phases:
            if not isinstance(phase, dict):
                continue

            targets = phase.get("targets", [])
            if not isinstance(targets, list):
                continue

            valid_targets: list[dict[str, Any]] = []
            for target in targets:
                if not isinstance(target, dict):
                    continue

                raw_url = target.get("url", "")
                url = str(raw_url)

                if not url.strip():
                    removed_count += 1
                    logger.warning(
                        "config_removed_empty_url_target",
                        phase_name=phase.get("name", "unnamed"),
                    )
                    continue

                if url.strip() in {"{{base_url}}", "{{url}}", "{url}", "{base_url}"}:
                    target["url"] = source_url
                    fixed_count += 1
                    logger.info(
                        "config_fixed_placeholder_url",
                        original=url,
                        fixed=source_url,
                    )

                valid_targets.append(target)

            phase["targets"] = valid_targets

        if fixed_count > 0 or removed_count > 0:
            logger.info(
                "config_sanitized_urls",
                fixed=fixed_count,
                removed=removed_count,
            )

        return config

    def _ensure_crawl_plan_has_targets(self, config: dict[str, Any], source_url: str) -> dict[str, Any]:
        """Ensure config has at least one valid target in either phases or crawl_targets."""
        crawl_targets = config.get("crawl_targets", [])
        has_valid_crawl_targets = False

        if isinstance(crawl_targets, list):
            for target in crawl_targets:
                if isinstance(target, dict):
                    url = target.get("url")
                    if isinstance(url, str) and url.strip():
                        has_valid_crawl_targets = True
                        break

        crawl_plan = config.get("crawl_plan", {})
        if not isinstance(crawl_plan, dict):
            crawl_plan = {}

        phases = crawl_plan.get("phases", [])
        has_valid_phase_targets = False

        if isinstance(phases, list):
            for phase in phases:
                if isinstance(phase, dict) and len(phase.get("targets", [])) > 0:
                    has_valid_phase_targets = True
                    break

        if not has_valid_crawl_targets and not has_valid_phase_targets:
            logger.warning("config_no_valid_targets_adding_default")
            crawl_plan["phases"] = [
                {
                    "name": "homepage",
                    "targets": [
                        {
                            "url": source_url,
                            "type": "seed",
                        }
                    ],
                }
            ]
            config["crawl_plan"] = crawl_plan
        elif has_valid_crawl_targets:
            logger.info(
                "config_has_valid_crawl_targets",
                count=len(
                    [
                        target
                        for target in crawl_targets
                        if isinstance(target, dict) and target.get("url")
                    ]
                ),
            )
        elif has_valid_phase_targets:
            logger.info("config_has_valid_phase_targets", count=len(phases))

        # CRITICAL: Ensure crawl_plan always exists (required by schema)
        if "crawl_plan" not in config:
            config["crawl_plan"] = {}

        # Ensure phases array exists and is non-empty (schema requirement)
        # If using crawl_targets, add a dummy phase to satisfy schema
        if "phases" not in config["crawl_plan"] or not config["crawl_plan"]["phases"]:
            # Add a minimal dummy phase (will be ignored by crawler when crawl_targets exist)
            config["crawl_plan"]["phases"] = [
                {
                    "name": "crawl_targets_mode",
                    "description": "Using crawl_targets, not phase-based crawling",
                }
            ]
            logger.info("config_added_dummy_phase_for_schema")

        return config

    def _validate_and_clean_crawl_targets(self, config: dict[str, Any]) -> dict[str, Any]:
        """Validate crawl_targets have full fetchable URLs."""
        crawl_targets = config.get("crawl_targets", [])
        if not isinstance(crawl_targets, list):
            return config

        valid_targets: list[dict[str, Any]] = []
        removed_count = 0

        for target in crawl_targets:
            if not isinstance(target, dict):
                removed_count += 1
                continue

            url = target.get("url")
            if not isinstance(url, str):
                removed_count += 1
                continue

            clean_url = url.strip()
            if not clean_url.startswith(("http://", "https://")):
                removed_count += 1
                logger.warning("crawl_target_invalid_url", url=url, reason="missing_protocol")
                continue

            if clean_url in {"{{base_url}}", "{{url}}", "{url}", "{base_url}"}:
                removed_count += 1
                logger.warning("crawl_target_invalid_url", url=url, reason="placeholder")
                continue

            target["url"] = clean_url
            valid_targets.append(target)

        if removed_count > 0:
            config["crawl_targets"] = valid_targets
            logger.info(
                "crawl_targets_cleaned",
                original=len(crawl_targets),
                valid=len(valid_targets),
                removed=removed_count,
            )

        if len(valid_targets) == 0 and len(crawl_targets) > 0:
            config.pop("crawl_targets", None)
            logger.warning("crawl_targets_all_invalid_removed")

        return config

    def _flatten_phases_to_crawl_targets(self, config: dict[str, Any]) -> dict[str, Any]:
        """Convert crawl_plan.phases[].targets[] to crawl_targets[] for crawler compatibility.

        OpenAI keeps generating phases structure even when prompted to emit crawl_targets.
        This transforms it to what the crawler expects, merging with any existing crawl_targets.
        """
        crawl_plan = config.get("crawl_plan", {})
        if not isinstance(crawl_plan, dict):
            return config

        phases = crawl_plan.get("phases", [])
        if not isinstance(phases, list) or not phases:
            return config

        # Get existing targets (might be from OpenAI or empty)
        existing_targets = config.get("crawl_targets", [])
        if not isinstance(existing_targets, list):
            existing_targets = []

        # Extract targets from phases
        phase_targets: list[dict[str, Any]] = []
        for phase in phases:
            if not isinstance(phase, dict):
                continue

            targets = phase.get("targets", [])
            if not isinstance(targets, list):
                continue

            for target in targets:
                if not isinstance(target, dict):
                    continue

                raw_url = target.get("url")
                if not isinstance(raw_url, str):
                    continue

                url = raw_url.strip()
                if not url:
                    continue

                crawl_target: dict[str, Any] = {"url": url}
                if "limit" in target:
                    crawl_target["limit"] = target["limit"]

                phase_targets.append(crawl_target)

        # Merge: add phase targets that aren't already in existing_targets
        existing_urls = {
            target.get("url")
            for target in existing_targets
            if isinstance(target, dict)
        }
        new_targets = [target for target in phase_targets if target.get("url") not in existing_urls]

        if new_targets:
            config["crawl_targets"] = existing_targets + new_targets
            logger.info(
                "config_merged_phase_targets",
                existing_count=len(existing_targets),
                phase_count=len(phase_targets),
                new_count=len(new_targets),
                total_count=len(config["crawl_targets"]),
            )
        elif existing_targets:
            logger.info(
                "config_already_has_crawl_targets",
                count=len(existing_targets),
            )
        elif phase_targets:
            config["crawl_targets"] = phase_targets
            logger.info(
                "config_flattened_phases_to_targets",
                phases_count=len(phases),
                targets_count=len(phase_targets),
            )
        else:
            logger.warning("config_no_valid_targets_in_phases")

        return config

    def _ensure_homepage_navigation_rule(self, config: dict[str, Any]) -> dict[str, Any]:
        """Add a homepage discovery rule to avoid crawl/extraction mismatch."""
        extraction_rules = config.get("extraction_rules", {})
        if not isinstance(extraction_rules, dict):
            return config

        has_homepage_rule = False
        for rule in extraction_rules.values():
            if not isinstance(rule, dict):
                continue

            identifiers = rule.get("identifiers", [])
            if not isinstance(identifiers, list):
                continue

            for identifier in identifiers:
                ident = str(identifier).strip()
                if ident in {"^/$", "/", "^/index", "^/home"}:
                    has_homepage_rule = True
                    break
            if has_homepage_rule:
                break

        if has_homepage_rule:
            logger.info("config_already_has_homepage_rule")
            return config

        extraction_rules["_Navigation"] = {
            "identifiers": ["^/$", "/", "/.*", "^$", "^/index", "^/home"],
            "css_selectors": {
                "links": (
                    "a[href*='/artists'], a[href*='/exhibitions'], a[href*='/news'], "
                    "a[href*='/galleries'], nav a, header a"
                )
            },
        }
        config["extraction_rules"] = extraction_rules
        logger.info("config_added_homepage_navigation_rule")
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
                    result[entity] = smart_html_preview(page.html, max_chars=3000)
        return result

    def validate_config(self, config: dict[str, Any]) -> None:
        extraction_rules = config.get("extraction_rules", {})
        if not isinstance(extraction_rules, dict) or not extraction_rules:
            raise ValueError("Config must include non-empty extraction_rules.")

        for page_type, rule in extraction_rules.items():
            identifiers = rule.get("identifiers", [])
            if not identifiers or not isinstance(identifiers, list) or len(identifiers) == 0:
                raise ValueError(
                    f"extraction_rules.{page_type}.identifiers must be a non-empty list. "
                    "OpenAI generated an empty or invalid identifiers array. "
                    f"Expected format: ['/{str(page_type).lower()}/[^/]+/?$'] or similar URL pattern. "
                    "This is usually a prompt issue - the model didn't understand identifier requirements."
                )
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
        return compact_prompt(
            "Generate JSON mining config. CRITICAL STRUCTURE: "
            "1. Use 'crawl_targets' array (NOT 'crawl_plan.phases') for simple crawls. "
            "2. Each crawl_target: {'url': 'full_url_here'} or {'url_pattern': 'pattern', "
            "'base_url': 'base'}. "
            "3. extraction_rules MUST be dict keyed by page type (e.g., {'Artists': {...}}), "
            "NOT a list. "
            "4. Each extraction_rule MUST have non-empty 'identifiers' array with URL patterns. "
            "5. Use 'css_selectors' (not 'selectors'). "
            "NEVER use empty identifiers []. "
            "Required top-level keys: crawl_targets, extraction_rules, page_type_rules, "
            "record_type_rules, follow_rules.",
            max_chars=420,
        )

    def _build_user_prompt(
        self,
        source_url: str,
        analysis: SiteAnalysis,
        sample_pages: dict[str, str],
    ) -> str:
        site_type = analysis.get("site_type", "unknown")
        cms = analysis.get("cms_platform", "unknown")
        entities = analysis.get("entity_types", [])
        normalized_entities = [str(entity).lower() for entity in entities]

        identifier_examples: list[str] = []
        if "artists" in normalized_entities or "artist" in normalized_entities:
            identifier_examples.append(
                "For Artists pages, use pattern like: '/artists/[^/]+/?$' or '/artist/[^/]+/?$'"
            )
        if "artworks" in normalized_entities or "artwork" in normalized_entities:
            identifier_examples.append(
                "For Artworks pages, use pattern like: '/artworks/[^/]+/?$' or '/art/[^/]+/?$'"
            )
        if "exhibitions" in normalized_entities or "exhibition" in normalized_entities:
            identifier_examples.append(
                "For Exhibitions, use pattern like: '/exhibitions/[^/]+/?$'"
            )

        prompt_parts = [
            f"Site URL: {source_url}",
            f"Site type: {site_type}",
            f"CMS: {cms}",
            f"Entity types: {', '.join(str(entity) for entity in entities)}",
            "",
            "STRUCTURE EXAMPLE:",
            "{",
            '  "crawl_targets": [',
            f'    {{"url": "{source_url}"}}',
            "  ],",
            '  "extraction_rules": {',
            '    "Artists": {',
            '      "identifiers": ["/artists/[^/]+/?$"],',
            '      "css_selectors": {...}',
            "    }",
            "  }",
            "}",
            "",
            "CRITICAL RULES:",
            "- Use crawl_targets array, NOT crawl_plan.phases",
            "- Every extraction_rule MUST have 'identifiers' with at least one URL pattern",
            "- NEVER use empty identifiers: []",
            "- Use specific regex patterns, not broad catch-alls like '/'",
            "- Return robust fallback selectors like 'h1.title, h1, h2'",
            "- Use specific URL patterns in identifiers",
        ]

        if identifier_examples:
            prompt_parts.append("")
            prompt_parts.append("Example identifier patterns:")
            prompt_parts.extend(identifier_examples)

        if sample_pages:
            prompt_parts.append("")
            prompt_parts.append("Sample pages from site:")
            for page_type, sample_html in sample_pages.items():
                prompt_parts.append(f"{page_type}: {sample_html}")

        return "\n".join(prompt_parts)
