from __future__ import annotations

from dataclasses import asdict, dataclass
from urllib.parse import parse_qs, urlparse

SUPPORTED_PAGE_TYPES = {"listing", "detail", "artist", "artwork", "exhibition", "document", "generic"}
EXCLUDE_PATH_TOKENS = ("/login", "/account", "/cart", "/search", "/privacy", "/terms")
UTILITY_TOKENS = ("privacy", "terms", "contact", "about", "cookie", "sitemap", "rss", "feed")
LISTING_TOKENS = ("artists", "artworks", "exhibitions", "events", "news", "blog", "index", "archive")
ARCHIVE_TOKENS = ("archive", "archives", "year", "past")


@dataclass(slots=True)
class FamilyRule:
    family_key: str
    path_pattern: str
    page_type: str
    include: bool
    follow_links: bool
    crawl_priority: str
    pagination_mode: str
    freshness_policy: str
    confidence: float
    rationale: str
    diagnostics_summary: dict[str, object]


def _depth(pattern: str) -> int:
    return len([p for p in pattern.split("/") if p])


def _infer_page_type(path_pattern: str, diagnostics: dict[str, object] | None = None) -> str:
    pattern = path_pattern.lower()
    diagnostics = diagnostics or {}
    dom_signals = str(diagnostics.get("dom_signals", "")).lower()
    signal_blob = f"{pattern} {dom_signals}"
    if any(token in signal_blob for token in ("artist", "/artists/")):
        return "artist"
    if any(token in signal_blob for token in ("artwork", "/works/", "/artworks/")):
        return "artwork"
    if any(token in signal_blob for token in ("exhibition", "event", "show")):
        return "exhibition"
    if any(token in signal_blob for token in (".pdf", "document", "catalogue", "catalog")):
        return "document"
    if any(token in signal_blob for token in LISTING_TOKENS):
        return "listing"
    if _depth(pattern) >= 3:
        return "detail"
    return "generic"


def resolve_page_type(candidate: str, confidence: float, path_pattern: str, diagnostics: dict[str, object] | None = None) -> tuple[str, bool]:
    mapped_candidate = {
        "listing": "listing",
        "generic_detail": "detail",
        "artist": "artist",
        "artwork": "artwork",
        "exhibition": "exhibition",
        "event": "exhibition",
        "document": "document",
    }.get(candidate.lower(), "generic")
    fallback = _infer_page_type(path_pattern, diagnostics)
    conflict = mapped_candidate != fallback and confidence < 0.72

    if confidence >= 0.72 and mapped_candidate in SUPPORTED_PAGE_TYPES:
        return mapped_candidate, False
    if fallback in SUPPORTED_PAGE_TYPES:
        return fallback, conflict
    return "generic", conflict


def decide_include(path_pattern: str, confidence: float, diagnostics: dict[str, object] | None = None, page_type: str = "generic") -> bool:
    diagnostics = diagnostics or {}
    path_lower = path_pattern.lower()
    if any(token in path_lower for token in EXCLUDE_PATH_TOKENS):
        return False
    if page_type == "document" and any(token in path_lower for token in ("/privacy", "/terms")):
        return False
    if any(token in path_lower for token in UTILITY_TOKENS):
        return False

    cluster_size = int(diagnostics.get("cluster_size", 1) or 1)
    if confidence < 0.35 and cluster_size <= 1:
        return False
    if cluster_size >= 3:
        return True
    if confidence >= 0.7:
        return True
    return page_type in {"listing", "artist", "artwork", "exhibition", "detail"} and confidence >= 0.45


def detect_pagination_mode(sample_urls: list[str], path_pattern: str = "") -> str:
    for url in sample_urls:
        query = parse_qs(urlparse(url).query)
        if "page" in query or "p" in query:
            return "query_param"
    if "/page/" in path_pattern.lower():
        return "path_segment"
    for url in sample_urls:
        if "/page/" in urlparse(url).path.lower():
            return "path_segment"
    return "none"


def build_family_rule(family) -> FamilyRule:
    diagnostics = family.get("diagnostics") or {}
    page_type, conflict = resolve_page_type(
        family.get("page_type_candidate", "generic"),
        float(family.get("confidence", 0.0)),
        family.get("path_pattern", "/"),
        diagnostics,
    )
    include = decide_include(
        family.get("path_pattern", "/"),
        float(family.get("confidence", 0.0)),
        diagnostics,
        page_type=page_type,
    )
    follow_links = page_type == "listing"
    pagination_mode = detect_pagination_mode(family.get("sample_urls", []), family.get("path_pattern", ""))
    priority = "high" if page_type == "listing" else "medium" if page_type in {"detail", "artist", "artwork", "exhibition"} else "low"
    freshness = "daily" if page_type == "listing" else "monthly" if any(
        token in family.get("path_pattern", "").lower() for token in ARCHIVE_TOKENS
    ) else "weekly"
    rationale = (
        f"candidate={family.get('page_type_candidate')} resolved={page_type} confidence={float(family.get('confidence', 0.0)):.2f} "
        f"cluster_size={int(diagnostics.get('cluster_size', 1) or 1)} include={include}"
    )
    diag_summary = {
        "cluster_size": int(diagnostics.get("cluster_size", 1) or 1),
        "avg_out_links": diagnostics.get("avg_out_links"),
        "llm_escalation_eligible": bool(conflict and float(family.get("confidence", 0.0)) < 0.55),
        "signals_conflict": conflict,
    }
    return FamilyRule(
        family_key=family["family_key"],
        path_pattern=family["path_pattern"],
        page_type=page_type,
        include=include,
        follow_links=follow_links,
        crawl_priority=priority,
        pagination_mode=pagination_mode,
        freshness_policy=freshness,
        confidence=float(family.get("confidence", 0.0)),
        rationale=rationale,
        diagnostics_summary=diag_summary,
    )


def build_mapping_json(source_id: str, profile_id: str, families: list[dict[str, object]]) -> dict[str, object]:
    rules = [build_family_rule(family) for family in families]
    return {
        "source_id": source_id,
        "based_on_profile_id": profile_id,
        "status": "draft",
        "family_rules": [asdict(rule) for rule in rules],
    }

