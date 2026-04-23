from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import structlog

logger = structlog.get_logger()

MIN_TEMPLATE_MATCH_THRESHOLD = 0.75


@dataclass
class TemplateMatch:
    template_id: str
    score: float


class TemplateLibrary:
    def __init__(self, template_dir: str | Path | None = None) -> None:
        if template_dir is None:
            template_dir = Path(__file__).resolve().parent / "template_data"
        self.template_dir = Path(template_dir)
        self.template_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, template_id: str) -> Path:
        return self.template_dir / f"{template_id}.json"

    def list_templates(self) -> list[dict[str, Any]]:
        templates: list[dict[str, Any]] = []
        for path in sorted(self.template_dir.glob("*.json")):
            templates.append(self._load_file(path))
        return templates

    def get_template(self, template_id: str) -> dict[str, Any] | None:
        path = self._path(template_id)
        if not path.exists():
            return None
        return self._load_file(path)

    def create_template(self, template: dict[str, Any]) -> dict[str, Any]:
        template_id = str(template["id"])
        payload = deepcopy(template)
        payload.setdefault("usage_count", 0)
        path = self._path(template_id)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def update_template(self, template_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"Template '{template_id}' not found")
        template.update(updates)
        self._path(template_id).write_text(json.dumps(template, indent=2), encoding="utf-8")
        return template

    def delete_template(self, template_id: str) -> bool:
        path = self._path(template_id)
        if not path.exists():
            return False
        path.unlink()
        return True

    def increment_usage(self, template_id: str) -> None:
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"Template '{template_id}' not found")
        template["usage_count"] = int(template.get("usage_count", 0)) + 1
        self._path(template_id).write_text(json.dumps(template, indent=2), encoding="utf-8")

    def match_template(self, analysis: dict[str, Any], threshold: float = MIN_TEMPLATE_MATCH_THRESHOLD) -> TemplateMatch | None:
        best: TemplateMatch | None = None
        for template in self.list_templates():
            score = self._score(template, analysis)
            if score < threshold:
                continue
            match = TemplateMatch(template_id=template["id"], score=score)
            if best is None or match.score > best.score:
                best = match
        if best:
            logger.info("template_match", template_id=best.template_id, score=best.score)
        else:
            logger.info("template_match_none")
        return best

    def apply_template(self, template_id: str, url: str) -> dict[str, Any]:
        template = self.get_template(template_id)
        if template is None:
            raise ValueError(f"Template '{template_id}' not found")

        domain = (urlparse(url).hostname or "").lower()
        config = deepcopy(template.get("config", {}))

        def _replace(value: Any) -> Any:
            if isinstance(value, str):
                return value.replace("{url}", url).replace("{domain}", domain)
            if isinstance(value, list):
                return [_replace(v) for v in value]
            if isinstance(value, dict):
                return {k: _replace(v) for k, v in value.items()}
            return value

        return _replace(config)

    @staticmethod
    def _load_file(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _score(template: dict[str, Any], analysis: dict[str, Any]) -> float:
        weights = {
            "site_type": 0.35,
            "cms_platform": 0.25,
            "entity_types": 0.25,
            "url_patterns": 0.15,
        }
        profile = template.get("profile", {})

        score = 0.0
        if profile.get("site_type") and profile.get("site_type") == analysis.get("site_type"):
            score += weights["site_type"]

        if profile.get("cms_platform") and profile.get("cms_platform") == analysis.get("cms_platform"):
            score += weights["cms_platform"]

        expected_entities = set(profile.get("entity_types", []))
        actual_entities = set(analysis.get("entity_types", []))
        if expected_entities and actual_entities:
            overlap = len(expected_entities & actual_entities) / max(1, len(expected_entities))
            score += weights["entity_types"] * overlap

        expected_patterns = profile.get("url_pattern_tokens", [])
        analysis_patterns = json.dumps(analysis.get("url_patterns", {})).lower()
        if expected_patterns:
            hits = sum(1 for token in expected_patterns if token.lower() in analysis_patterns)
            score += weights["url_patterns"] * (hits / len(expected_patterns))

        return round(score, 4)
