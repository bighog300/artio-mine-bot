from __future__ import annotations

import json
from urllib.parse import urljoin

from app.crawler.crawl_policy import score_url
from app.crawler.site_structure_analyzer import _generate_urls_from_pattern
from app.crawler.url_utils import normalize_url


def build_seed_rows(
    *,
    root_url: str,
    structure_map: str | None,
) -> list[dict[str, str | int]]:
    """Build initial durable-frontier rows from root URL and structure targets."""
    rows: list[dict[str, str | int]] = []
    seen: set[str] = set()

    def _add_seed(url: str, depth: int = 0) -> None:
        normalized = normalize_url(url)
        if normalized in seen:
            return
        seen.add(normalized)
        priority, predicted_page_type = score_url(url, structure_map)
        rows.append(
            {
                "url": url,
                "normalized_url": normalized,
                "depth": depth,
                "status": "queued",
                "priority": priority,
                "predicted_page_type": predicted_page_type,
                "discovered_from_page_type": "seed",
                "discovery_reason": "seed_root" if depth == 0 and normalized == normalize_url(root_url) else "seed_structure_target",
            }
        )

    if structure_map:
        try:
            payload = json.loads(structure_map)
        except json.JSONDecodeError:
            payload = {}
        for target in payload.get("crawl_targets", []):
            pattern = target.get("url_pattern")
            if not pattern:
                continue
            for generated_url in _generate_urls_from_pattern(
                root_url,
                pattern,
                limit=int(target.get("estimated_pages", 100)),
            ):
                _add_seed(urljoin(root_url, generated_url), depth=0)

    _add_seed(root_url, depth=0)
    return rows
