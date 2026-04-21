import re
from collections import defaultdict
from urllib.parse import urlparse

from app.source_profiler.types import ProfiledPage, UrlFamilyCluster


_PAGE_TYPE_HINTS: tuple[tuple[str, str], ...] = (
    ("artist", "artist"),
    ("artwork", "artwork"),
    ("exhibition", "exhibition"),
    ("event", "event"),
    ("venue", "venue"),
    ("gallery", "venue"),
    ("news", "listing"),
    ("blog", "listing"),
)


def _normalize_segment(segment: str) -> str:
    if segment.isdigit():
        return "{num}"
    if re.fullmatch(r"[0-9a-f]{8,}", segment):
        return "{hex}"
    if re.search(r"\d", segment):
        return "{slug}"
    return segment


def _path_pattern(url: str) -> str:
    path = urlparse(url).path.strip("/")
    if not path:
        return "/"
    parts = [_normalize_segment(part.lower()) for part in path.split("/") if part]
    return "/" + "/".join(parts)


def _page_type_candidate(pattern: str) -> str:
    lower = pattern.lower()
    for token, page_type in _PAGE_TYPE_HINTS:
        if token in lower:
            return page_type
    depth = len([part for part in lower.split("/") if part])
    return "listing" if depth <= 1 else "generic_detail"


def cluster_profiled_pages(pages: list[ProfiledPage]) -> list[UrlFamilyCluster]:
    buckets: dict[str, list[ProfiledPage]] = defaultdict(list)
    for page in pages:
        buckets[_path_pattern(page.url)].append(page)

    total = max(len(pages), 1)
    clusters: list[UrlFamilyCluster] = []
    for pattern, members in buckets.items():
        page_type = _page_type_candidate(pattern)
        family_key = f"{page_type}:{pattern}"
        label = f"{page_type.replace('_', ' ').title()} {pattern}"
        confidence = 0.45 + (len(members) / total) * 0.5
        if page_type != "generic_detail":
            confidence += 0.1
        out_links = sum(len(item.out_links) for item in members)
        clusters.append(
            UrlFamilyCluster(
                family_key=family_key,
                family_label=label,
                path_pattern=pattern,
                page_type_candidate=page_type,
                confidence=round(min(confidence, 0.98), 2),
                sample_urls=[item.url for item in members[:5]],
                diagnostics={
                    "cluster_size": len(members),
                    "avg_out_links": round(out_links / max(len(members), 1), 2),
                },
            )
        )
    return sorted(clusters, key=lambda item: (-item.confidence, item.path_pattern))
