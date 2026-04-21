import pytest

from app.source_profiler.clustering import cluster_profiled_pages
from app.source_profiler.types import ProfiledPage


def test_cluster_profiled_pages_groups_artist_and_events_families():
    pages = [
        ProfiledPage(url="https://site.test/"),
        ProfiledPage(url="https://site.test/artists"),
        ProfiledPage(url="https://site.test/artists/jane-doe"),
        ProfiledPage(url="https://site.test/events"),
        ProfiledPage(url="https://site.test/events/opening-night"),
    ]
    clusters = cluster_profiled_pages(pages)
    patterns = {cluster.path_pattern for cluster in clusters}
    assert "/artists" in patterns
    assert "/artists/jane-doe" in patterns
    assert any(cluster.page_type_candidate == "artist" for cluster in clusters)
    assert any(cluster.page_type_candidate == "event" for cluster in clusters)


@pytest.mark.asyncio
async def test_profile_endpoint_returns_families_and_metrics(test_client):
    source_resp = await test_client.post("/api/sources", json={"url": "https://profiler-one.test"})
    source_id = source_resp.json()["id"]

    profile_resp = await test_client.post(
        f"/api/sources/{source_id}/profiles",
        json={"max_pages": 30},
    )
    assert profile_resp.status_code == 201
    payload = profile_resp.json()
    assert payload["source_id"] == source_id
    assert payload["status"] == "completed"
    assert payload["site_fingerprint"]["host"] == "profiler-one.test"
    assert len(payload["families"]) >= 2
    assert payload["profile_metrics"]["families_count"] >= 2


@pytest.mark.asyncio
async def test_profile_get_endpoint_loads_persisted_profile(test_client):
    source_resp = await test_client.post("/api/sources", json={"url": "https://profiler-two.test"})
    source_id = source_resp.json()["id"]
    created = await test_client.post(f"/api/sources/{source_id}/profiles", json={})
    profile_id = created.json()["id"]

    get_resp = await test_client.get(f"/api/sources/{source_id}/profiles/{profile_id}")
    assert get_resp.status_code == 200
    payload = get_resp.json()
    assert payload["id"] == profile_id
    assert payload["nav_discovery_summary"]["entrypoints"]
    assert any(item["confidence"] >= 0.5 for item in payload["families"])
