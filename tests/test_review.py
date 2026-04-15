import json
from unittest.mock import AsyncMock, patch

import pytest

from app.db import crud


@pytest.mark.asyncio
async def test_review_artist_detail_includes_conflicts_and_provenance(test_client, db_session):
    source = await crud.create_source(db_session, url="https://review.example")
    record = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Alice",
        raw_data=json.dumps(
            {
                "artist_family_key": "review.example::alice",
                "artist_payload": {"artist_name": "Alice", "birth_year": 1950},
                "completeness_score": 72,
                "missing_fields": ["email"],
                "provenance": {"birth_year": {"value": 1950, "sources": [{"source_url": "https://review.example/alice/about.php"}]}},
                "conflicts": {
                    "birth_year": [
                        {"value": 1950, "source_url": "https://review.example/alice/about.php", "selected": True},
                        {"value": 1952, "source_url": "https://review.example/alice/", "selected": False},
                    ]
                },
                "related": {"articles": [{"title": "Interview"}]},
            }
        ),
    )

    resp = await test_client.get(f"/api/review/artists/{record.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["completeness_score"] == 72
    assert "birth_year" in body["conflicts"]
    assert "birth_year" in body["provenance"]


@pytest.mark.asyncio
async def test_review_artists_filtering(test_client, db_session):
    source = await crud.create_source(db_session, url="https://review-filter.example")
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Complete",
        raw_data=json.dumps({"completeness_score": 90, "missing_fields": [], "conflicts": {}}),
    )
    await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Needs Review",
        raw_data=json.dumps(
            {
                "completeness_score": 20,
                "missing_fields": ["bio"],
                "conflicts": {"birth_year": [{"value": 1}]},
            }
        ),
    )

    resp = await test_client.get("/api/review/artists?completeness_lt=30&has_conflicts=true")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["title"] == "Needs Review"


@pytest.mark.asyncio
async def test_resolve_conflict_updates_selected_value(test_client, db_session):
    source = await crud.create_source(db_session, url="https://resolve.example")
    record = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Resolvable",
        raw_data=json.dumps(
            {
                "artist_payload": {"birth_year": 1950},
                "provenance": {"birth_year": {"value": 1950, "sources": []}},
                "conflicts": {
                    "birth_year": [
                        {"value": 1950, "selected": True, "resolved": False},
                        {"value": 1952, "selected": False, "resolved": False},
                    ]
                },
            }
        ),
    )

    resp = await test_client.post(
        f"/api/review/artists/{record.id}/resolve",
        json={"field": "birth_year", "selected_value": 1952},
    )
    assert resp.status_code == 200

    refreshed = await crud.get_record(db_session, record.id)
    payload = json.loads(refreshed.raw_data)
    assert payload["artist_payload"]["birth_year"] == 1952
    assert payload["resolved_conflicts"]["birth_year"]["selected_value"] == 1952


@pytest.mark.asyncio
async def test_rerun_artist_family_endpoint(test_client, db_session):
    source = await crud.create_source(db_session, url="https://rerun.example")
    record = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Rerun",
        source_url="https://rerun.example/alice/",
        raw_data=json.dumps({"artist_family_key": "rerun.example::alice"}),
    )

    with patch(
        "app.api.routes.review.PipelineRunner.rerun_artist_family",
        new=AsyncMock(return_value={"family_key": "rerun.example::alice", "pages_reprocessed": 3}),
    ):
        resp = await test_client.post(f"/api/review/artists/{record.id}/rerun")

    assert resp.status_code == 200
    body = resp.json()
    assert body["result"]["pages_reprocessed"] == 3
