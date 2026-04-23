import pytest

from app.source_mapper.mapping_suggestion import (
    build_family_rule,
    decide_include,
    detect_pagination_mode,
    resolve_page_type,
)


def test_include_exclude_logic_blocks_utility_and_low_confidence_singletons():
    assert not decide_include("/account/profile", 0.92, {"cluster_size": 4}, page_type="detail")
    assert not decide_include("/misc/page", 0.2, {"cluster_size": 1}, page_type="generic")
    assert decide_include("/artists", 0.5, {"cluster_size": 6}, page_type="listing")


def test_page_type_fallback_inference_maps_generic_detail_to_detail_and_keywords():
    resolved, conflict = resolve_page_type("generic_detail", 0.4, "/artists/jane-doe", {})
    assert resolved == "artist"
    assert conflict

    resolved_high, conflict_high = resolve_page_type("artwork", 0.9, "/foo/bar", {})
    assert resolved_high == "artwork"
    assert not conflict_high


def test_pagination_detection_handles_query_and_path_segment():
    assert detect_pagination_mode(["https://x.test/news?page=2"], "/news") == "query_param"
    assert detect_pagination_mode(["https://x.test/blog/page/3"], "/blog/page/{num}") == "path_segment"
    assert detect_pagination_mode(["https://x.test/about"], "/about") == "none"


def test_priority_assignment_uses_page_type_defaults():
    listing = build_family_rule(
        {
            "family_key": "listing:/artists",
            "path_pattern": "/artists",
            "page_type_candidate": "listing",
            "confidence": 0.8,
            "sample_urls": ["https://x.test/artists?page=1"],
            "diagnostics": {"cluster_size": 8, "avg_out_links": 12},
        }
    )
    document = build_family_rule(
        {
            "family_key": "doc:/catalog.pdf",
            "path_pattern": "/catalog.pdf",
            "page_type_candidate": "document",
            "confidence": 0.86,
            "sample_urls": ["https://x.test/catalog.pdf"],
            "diagnostics": {"cluster_size": 2, "avg_out_links": 0},
        }
    )
    assert listing.crawl_priority == "high"
    assert listing.follow_links is True
    assert listing.freshness_policy == "daily"
    assert document.crawl_priority == "low"


@pytest.mark.asyncio
async def test_profile_to_mapping_draft_generation_and_retrieval(test_client):
    source_resp = await test_client.post("/api/sources", json={"url": "https://phase2-map.test"})
    source_id = source_resp.json()["id"]

    profile_resp = await test_client.post(f"/api/sources/{source_id}/profiles", json={"max_pages": 25})
    assert profile_resp.status_code == 201
    profile_id = profile_resp.json()["id"]

    draft_resp = await test_client.post(
        f"/api/sources/{source_id}/mappings/draft",
        json={"profile_id": profile_id},
    )
    assert draft_resp.status_code == 201
    draft_payload = draft_resp.json()
    assert draft_payload["status"] == "draft"
    assert draft_payload["based_on_profile_id"] == profile_id
    assert len(draft_payload["family_rules"]) >= 1
    assert {"family_key", "page_type", "include", "follow_links", "crawl_priority", "pagination_mode", "freshness_policy"}.issubset(
        set(draft_payload["family_rules"][0].keys())
    )

    mapping_id = draft_payload["id"]
    get_resp = await test_client.get(f"/api/sources/{source_id}/mappings/{mapping_id}")
    assert get_resp.status_code == 200
    get_payload = get_resp.json()
    assert get_payload["id"] == mapping_id
    assert get_payload["source_id"] == source_id
    assert get_payload["fields"] == []
