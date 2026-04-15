import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SourceMappingSampleResult, SourceMappingVersion


@pytest.mark.asyncio
async def test_create_source_scan_creates_draft_and_seed_rows(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-one.test"})
    source_id = source_resp.json()["id"]

    resp = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts",
        json={"max_pages": 20, "max_depth": 2, "sample_pages_per_type": 3},
    )
    assert resp.status_code == 201
    payload = resp.json()
    assert payload["source_id"] == source_id
    assert payload["status"] == "draft"
    assert payload["mapping_count"] >= 1


@pytest.mark.asyncio
async def test_mapping_rows_list_update_and_actions(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-two.test"})
    source_id = source_resp.json()["id"]
    draft_resp = await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})
    draft_id = draft_resp.json()["id"]

    rows_resp = await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")
    assert rows_resp.status_code == 200
    rows = rows_resp.json()["items"]
    assert len(rows) >= 1
    row_id = rows[0]["id"]

    patch_resp = await test_client.patch(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/{row_id}",
        json={"status": "needs_review", "destination_entity": "event", "destination_field": "title"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "needs_review"

    action_resp = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve"},
    )
    assert action_resp.status_code == 200
    assert action_resp.json()["updated"] == 1


@pytest.mark.asyncio
async def test_mapping_row_validation_error_on_invalid_destination(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-three.test"})
    source_id = source_resp.json()["id"]
    draft_resp = await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})
    draft_id = draft_resp.json()["id"]

    rows_resp = await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")
    row_id = rows_resp.json()["items"][0]["id"]

    patch_resp = await test_client.patch(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/{row_id}",
        json={"destination_entity": "event", "destination_field": "not_a_field"},
    )
    assert patch_resp.status_code == 400


@pytest.mark.asyncio
async def test_preview_generation_contract_and_persistence(test_client: AsyncClient, db_session: AsyncSession):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-four.test", "name": "Mapper Four"})
    source_id = source_resp.json()["id"]
    draft_resp = await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})
    draft_id = draft_resp.json()["id"]

    preview_resp = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/preview",
        json={"sample_page_id": "default"},
    )
    assert preview_resp.status_code == 200
    payload = preview_resp.json()
    assert payload["sample_page_id"]
    assert payload["page_url"].startswith("https://")
    assert isinstance(payload["extractions"], list)
    assert isinstance(payload["record_preview"], dict)

    version = (await db_session.execute(select(SourceMappingVersion).where(SourceMappingVersion.id == draft_id))).scalar_one()
    assert version.scan_status == "completed"

    results = (await db_session.execute(select(SourceMappingSampleResult))).scalars().all()
    assert len(results) >= 1
    saved_preview = json.loads(results[-1].record_preview_json)
    assert "record_preview" in saved_preview
