import json

from app.extraction.artist_merge import merge_artist_payload
from app.metrics import metrics


def test_provenance_tracking_and_multi_source_support():
    first = merge_artist_payload(
        existing_raw_data=None,
        page_type="artist_profile_hub",
        source_url="https://art.co.za/alice/",
        source_page_id="page-1",
        extracted_data={"name": "Alice", "bio": "Short", "birth_year": 1950},
        related_data={},
    )
    merged = merge_artist_payload(
        existing_raw_data=json.dumps(first),
        page_type="artist_biography",
        source_url="https://art.co.za/alice/about.php",
        source_page_id="page-2",
        extracted_data={"bio": "Long biography", "birth_year": 1952},
        related_data={},
    )

    assert merged["artist_payload"]["birth_year"] == 1950
    assert "birth_year" in merged["provenance"]
    assert len(merged["provenance"]["birth_year"]["sources"]) == 2
    assert merged["artist_payload"]["bio_full"] == "Long biography"


def test_conflicts_are_recorded_with_selected_and_alternatives():
    base = merge_artist_payload(
        existing_raw_data=None,
        page_type="artist_biography",
        source_url="https://site/a/about.php",
        source_page_id="page-a",
        extracted_data={"birth_year": 1950},
        related_data={},
    )
    merged = merge_artist_payload(
        existing_raw_data=json.dumps(base),
        page_type="artist_profile_hub",
        source_url="https://site/a/",
        source_page_id="page-hub",
        extracted_data={"birth_year": 1952},
        related_data={},
    )

    assert "birth_year" in merged["conflicts"]
    values = {entry["value"] for entry in merged["conflicts"]["birth_year"]}
    assert values == {1950, 1952}
    selected = [entry for entry in merged["conflicts"]["birth_year"] if entry["selected"]]
    assert len(selected) == 1


def test_metrics_snapshot_and_average_completeness():
    metrics.reset()
    metrics.increment("pages_processed", 2)
    metrics.increment("records_enriched", 1)
    metrics.observe_completeness(60)
    metrics.observe_completeness(80)
    snap = metrics.snapshot()
    assert snap["pages_processed"] == 2
    assert snap["records_enriched"] == 1
    assert snap["average_completeness"] == 70.0
