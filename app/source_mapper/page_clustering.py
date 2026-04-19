from collections import defaultdict
from urllib.parse import urlparse

from app.source_mapper.types import DiscoveredPage, PageCluster


KEYWORDS: tuple[tuple[str, str], ...] = (
    ("event", "Event Detail"),
    ("artist", "Artist Detail"),
    ("exhibition", "Exhibition Detail"),
    ("venue", "Venue Detail"),
    ("artwork", "Artwork Detail"),
)


def cluster_pages(pages: list[DiscoveredPage]) -> list[PageCluster]:
    buckets: dict[str, list[DiscoveredPage]] = defaultdict(list)
    for page in pages:
        path = urlparse(page.url).path.lower()
        key = "generic_detail"
        if path.rstrip("/") == "/artists":
            key = "artist_directory_root"
        elif path.startswith("/artists/") and len([part for part in path.split("/") if part]) == 2:
            key = "artist_directory_letter"
        elif path.endswith("/about.php"):
            key = "artist_biography"
        elif path.endswith("/art-classes.php"):
            key = "artist_related_page"
        elif len([part for part in path.split("/") if part]) == 1 and "." not in path:
            key = "artist_profile_hub"
        if key == "generic_detail":
            for token, cluster_label in KEYWORDS:
                if token in path:
                    key = cluster_label.lower().replace(" ", "_")
                    break
        buckets[key].append(page)

    clusters: list[PageCluster] = []
    for key, bucket in buckets.items():
        label = key.replace("_", " ").title()
        if key == "generic_detail":
            label = "Generic Detail"
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
