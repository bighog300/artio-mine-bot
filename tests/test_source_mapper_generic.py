from app.source_mapper.page_clustering import cluster_pages
from app.source_mapper.proposal_engine import build_proposals
from app.source_mapper.types import DiscoveredPage, PageCluster


def test_cluster_pages_uses_generic_roles_not_site_specific_paths():
    pages = [
        DiscoveredPage(url="https://generic.test/", title="Home"),
        DiscoveredPage(url="https://generic.test/people/alex", title="Alex"),
        DiscoveredPage(url="https://generic.test/calendar/opening-night", title="Opening Night"),
    ]

    clusters = cluster_pages(pages)
    keys = {cluster.key for cluster in clusters}

    assert "root_page" in keys
    assert "detail_page" in keys or "detail_event" in keys
    assert "detail_profile" in keys or "detail_page" in keys
    assert "artist_profile_hub" not in keys


def test_proposal_engine_builds_schema_aware_proposals():
    cluster = PageCluster(
        key="detail_content",
        label="Detail Content",
        confidence_score=0.82,
        sample_urls=["https://generic.test/content/1"],
    )

    proposals = build_proposals(cluster, source_name="Generic Source")

    assert proposals
    assert all(proposal.destination_entity in {"organization", "event", "artist"} for proposal in proposals)
    assert any("schema blueprint" in " ".join(proposal.rationale).lower() for proposal in proposals)
