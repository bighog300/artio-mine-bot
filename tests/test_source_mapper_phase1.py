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

    ignore_resp = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "ignore"},
    )
    assert ignore_resp.status_code == 200
    assert ignore_resp.json()["updated"] == 1


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


@pytest.mark.asyncio
async def test_low_confidence_requires_force_on_approve(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-low-confidence.test"})
    source_id = source_resp.json()["id"]
    draft_resp = await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})
    draft_id = draft_resp.json()["id"]
    row_id = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")).json()["items"][0]["id"]

    blocked = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve"},
    )
    assert blocked.status_code == 409

    forced = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve", "force_low_confidence": True},
    )
    assert forced.status_code == 200
    assert forced.json()["updated"] == 1


@pytest.mark.asyncio
async def test_publish_state_transition_and_version_clone_workflow(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-publish.test"})
    source_id = source_resp.json()["id"]
    draft_resp = await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})
    draft_id = draft_resp.json()["id"]
    row_id = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")).json()["items"][0]["id"]

    cannot_publish = await test_client.post(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/publish")
    assert cannot_publish.status_code == 409

    approve = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve", "force_low_confidence": True},
    )
    assert approve.status_code == 200

    publish = await test_client.post(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/publish")
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"

    cloned_draft = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts",
        json={"scan_mode": "edit_published"},
    )
    assert cloned_draft.status_code == 201
    assert cloned_draft.json()["status"] == "draft"

    versions = await test_client.get(f"/api/sources/{source_id}/mapping-drafts")
    assert versions.status_code == 200
    assert versions.json()["total"] >= 2


@pytest.mark.asyncio
async def test_preview_regression_includes_snippet_categories_and_warnings(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-preview-regression.test", "name": "Preview Regression"})
    source_id = source_resp.json()["id"]
    draft_id = (await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})).json()["id"]
    row = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")).json()["items"][0]

    await test_client.patch(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/{row['id']}",
        json={"category_target": "live-events"},
    )
    preview_resp = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/preview",
        json={"sample_page_id": "default"},
    )
    assert preview_resp.status_code == 200
    payload = preview_resp.json()
    assert "category_preview" in payload
    assert "warnings" in payload
    assert payload["source_snippet"] is None or isinstance(payload["source_snippet"], str)
    assert payload["record_preview"].get("title") is not None

    diff_resp = await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/diff")
    assert diff_resp.status_code == 200
    diff_payload = diff_resp.json()
    assert set(diff_payload.keys()) == {"added", "removed", "changed", "unchanged"}


@pytest.mark.asyncio
async def test_scan_endpoint_and_sample_run_flow(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-scan-flow.test"})
    source_id = source_resp.json()["id"]
    draft_id = (await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})).json()["id"]

    scan_resp = await test_client.post(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/scan")
    assert scan_resp.status_code == 202
    assert scan_resp.json()["scan_status"] in {"completed", "error", "queued"}

    sample_run_resp = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/sample-run",
        json={"sample_count": 3},
    )
    assert sample_run_resp.status_code == 202
    sample_run_id = sample_run_resp.json()["sample_run_id"]

    sample_results_resp = await test_client.get(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/sample-run/{sample_run_id}"
    )
    assert sample_results_resp.status_code == 200
    payload = sample_results_resp.json()
    assert payload["sample_run_id"] == sample_run_id
    assert isinstance(payload["items"], list)


@pytest.mark.asyncio
async def test_rollback_published_mapping_version(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-rollback.test"})
    source_id = source_resp.json()["id"]
    draft_id = (await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})).json()["id"]
    row_id = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")).json()["items"][0]["id"]
    await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve", "force_low_confidence": True},
    )
    publish = await test_client.post(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/publish")
    assert publish.status_code == 200
    version_id = publish.json()["id"]

    rollback = await test_client.post(f"/api/sources/{source_id}/mapping-drafts/versions/{version_id}/rollback")
    assert rollback.status_code == 200
    assert rollback.json()["id"] == version_id
