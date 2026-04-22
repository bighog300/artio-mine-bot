from collections import defaultdict
from urllib.parse import urlparse

from app.source_mapper.types import DiscoveredPage, PageCluster


ROLE_HINTS: tuple[tuple[str, str], ...] = (
    ("directory", "directory_index"),
    ("listing", "listing_page"),
    ("calendar", "listing_page"),
    ("event", "detail_event"),
    ("artist", "detail_profile"),
    ("venue", "detail_profile"),
    ("gallery", "detail_profile"),
    ("exhibit", "detail_content"),
    ("collection", "detail_content"),
    ("article", "detail_content"),
)


def _is_slug_detail(path: str) -> bool:
    parts = [part for part in path.split("/") if part]
    return len(parts) >= 2 and "." not in parts[-1]


def cluster_pages(pages: list[DiscoveredPage]) -> list[PageCluster]:
    buckets: dict[str, list[DiscoveredPage]] = defaultdict(list)
    for page in pages:
        path = urlparse(page.url).path.lower().rstrip("/") or "/"
        key = "generic_page"
        parts = [part for part in path.split("/") if part]
        if path == "/":
            key = "root_page"
        elif len(parts) == 1 and "." not in parts[0]:
            key = "section_landing"
        elif _is_slug_detail(path):
            key = "detail_page"
        for token, role in ROLE_HINTS:
            if token in path:
                key = role
                break
        buckets[key].append(page)

    clusters: list[PageCluster] = []
    for key, bucket in buckets.items():
        label = key.replace("_", " ").title()
        confidence = min(0.95, 0.5 + (len(bucket) / max(len(pages), 1)) * 0.5)
        clusters.append(
            PageCluster(
                key=key,
                label=label,
                confidence_score=round(confidence, 2),
                sample_urls=[item.url for item in bucket[:5]],
            )
        )
    return sorted(clusters, key=lambda item: item.key)
