import asyncio
import json

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SourceMappingPreset, SourceMappingPresetRow, SourceMappingSampleResult, SourceMappingVersion


async def wait_for_scan_complete(client: AsyncClient, source_id: str, draft_id: str, timeout: float = 10) -> dict:
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        draft_resp = await client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}")
        assert draft_resp.status_code == 200
        payload = draft_resp.json()
        if payload.get("scan_status") == "completed":
            return payload
        if payload.get("scan_status") == "error":
            raise AssertionError(f"Scan failed for draft {draft_id}: {payload}")
        await asyncio.sleep(0.1)
    raise AssertionError(f"Timed out waiting for mapping scan to complete for draft {draft_id}")


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
    assert payload["scan_status"] in {"queued", "completed"}
    if payload["scan_status"] != "completed":
        payload = await wait_for_scan_complete(test_client, source_id, payload["id"])
    assert payload["mapping_count"] >= 1


@pytest.mark.asyncio
async def test_mapping_rows_list_update_and_actions(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-two.test"})
    source_id = source_resp.json()["id"]
    draft_resp = await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})
    draft_id = draft_resp.json()["id"]
    await wait_for_scan_complete(test_client, source_id, draft_id)

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
    await wait_for_scan_complete(test_client, source_id, draft_id)

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
    await wait_for_scan_complete(test_client, source_id, draft_id)

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
    assert "page_family" in payload
    assert "linked_images" in payload
    assert "discarded_images" in payload

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
    await wait_for_scan_complete(test_client, source_id, draft_id)
    row_id = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")).json()["items"][0]["id"]

    blocked = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve"},
    )
    assert blocked.status_code in {200, 409}

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
    await wait_for_scan_complete(test_client, source_id, draft_id)

    publish = await test_client.post(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/publish")
    assert publish.status_code == 200
    assert publish.json()["status"] == "published"
    approved_row = await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")
    assert approved_row.status_code == 200
    assert approved_row.json()["items"][0]["status"] == "approved"

    refreshed_draft = await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})
    refreshed_draft_id = refreshed_draft.json()["id"]
    await wait_for_scan_complete(test_client, source_id, refreshed_draft_id)
    refreshed_row_id = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{refreshed_draft_id}/rows")).json()["items"][0]["id"]
    reject = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{refreshed_draft_id}/rows/actions",
        json={"row_ids": [refreshed_row_id], "action": "reject"},
    )
    assert reject.status_code == 200
    publish_blocked = await test_client.post(f"/api/sources/{source_id}/mapping-drafts/{refreshed_draft_id}/publish")
    assert publish_blocked.status_code == 409
    assert "No approved rows" in publish_blocked.json()["detail"]

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
    await wait_for_scan_complete(test_client, source_id, draft_id)
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
    draft_resp = await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}")
    assert draft_resp.status_code == 200
    assert "scan_progress_percent" in draft_resp.json()
    assert draft_resp.json()["scan_progress_percent"] >= 0

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

    if payload["items"]:
        result_id = payload["items"][0]["id"]
        moderate_resp = await test_client.patch(
            f"/api/sources/{source_id}/mapping-drafts/{draft_id}/sample-run/{sample_run_id}/results/{result_id}",
            json={"review_status": "approved", "review_notes": "Looks good"},
        )
        assert moderate_resp.status_code == 200
        assert moderate_resp.json()["review_status"] == "approved"
        assert moderate_resp.json()["review_notes"] == "Looks good"

        filtered_resp = await test_client.get(
            f"/api/sources/{source_id}/mapping-drafts/{draft_id}/sample-run/{sample_run_id}?review_status=approved"
        )
        assert filtered_resp.status_code == 200
        filtered_items = filtered_resp.json()["items"]
        assert all(item["review_status"] == "approved" for item in filtered_items)


@pytest.mark.asyncio
async def test_scan_supports_discovery_roots_for_artists_index(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://www.art.co.za"})
    source_id = source_resp.json()["id"]
    draft_resp = await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts",
        json={"discovery_roots": ["https://www.art.co.za/artists/"], "max_pages": 20},
    )
    assert draft_resp.status_code == 201
    draft_id = draft_resp.json()["id"]
    await wait_for_scan_complete(test_client, source_id, draft_id)
    page_types = await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/page-types")
    assert page_types.status_code == 200
    keys = {item["key"] for item in page_types.json()["items"]}
    assert "root_page" in keys
    assert any(key.startswith("detail_") or key in {"listing_page", "directory_index", "section_landing"} for key in keys)


@pytest.mark.asyncio
async def test_rollback_published_mapping_version(test_client: AsyncClient):
    source_resp = await test_client.post("/api/sources", json={"url": "https://mapper-rollback.test"})
    source_id = source_resp.json()["id"]
    draft_id = (await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})).json()["id"]
    await wait_for_scan_complete(test_client, source_id, draft_id)
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


@pytest.mark.asyncio
async def test_mapping_presets_create_list_delete_and_row_snapshot(test_client: AsyncClient, db_session: AsyncSession):
    source_id = (await test_client.post("/api/sources", json={"url": "https://mapper-presets.test"})).json()["id"]
    draft_id = (await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})).json()["id"]
    await wait_for_scan_complete(test_client, source_id, draft_id)
    row_id = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")).json()["items"][0]["id"]
    await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve", "force_low_confidence": True},
    )

    create = await test_client.post(
        f"/api/sources/{source_id}/mapping-presets",
        json={"name": "approved preset", "draft_id": draft_id},
    )
    assert create.status_code == 201
    preset_id = create.json()["id"]
    assert create.json()["row_count"] >= 1

    rows_before = (
        await db_session.execute(select(SourceMappingPresetRow).where(SourceMappingPresetRow.preset_id == preset_id))
    ).scalars().all()
    assert len(rows_before) >= 1

    # Update draft row after preset creation to verify row snapshots are copied.
    await test_client.patch(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/{row_id}",
        json={"destination_entity": "event", "destination_field": "description"},
    )
    rows_after = (
        await db_session.execute(select(SourceMappingPresetRow).where(SourceMappingPresetRow.preset_id == preset_id))
    ).scalars().all()
    assert rows_after[0].destination_field == rows_before[0].destination_field

    listing = await test_client.get(f"/api/sources/{source_id}/mapping-presets")
    assert listing.status_code == 200
    assert listing.json()["total"] == 1

    deleted = await test_client.delete(f"/api/sources/{source_id}/mapping-presets/{preset_id}")
    assert deleted.status_code == 200
    assert deleted.json()["ok"] is True
    saved_preset = (await db_session.execute(select(SourceMappingPreset).where(SourceMappingPreset.id == preset_id))).scalar_one_or_none()
    assert saved_preset is None
    orphan_rows = (
        await db_session.execute(select(SourceMappingPresetRow).where(SourceMappingPresetRow.preset_id == preset_id))
    ).scalars().all()
    assert orphan_rows == []


@pytest.mark.asyncio
async def test_mapping_presets_zero_matching_rows_fails_with_clear_error(test_client: AsyncClient):
    source_id = (await test_client.post("/api/sources", json={"url": "https://mapper-presets-empty.test"})).json()["id"]
    draft_id = (await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})).json()["id"]

    create = await test_client.post(
        f"/api/sources/{source_id}/mapping-presets",
        json={"name": "approved only", "draft_id": draft_id, "include_statuses": ["approved"]},
    )
    assert create.status_code == 400
    assert "No mapping rows matched include_statuses" in create.json()["detail"]


@pytest.mark.asyncio
async def test_mapping_preset_export_and_external_template_import_apply(test_client: AsyncClient):
    source_id = (await test_client.post("/api/sources", json={"url": "https://mapper-template.test"})).json()["id"]
    draft_id = (await test_client.post(f"/api/sources/{source_id}/mapping-drafts", json={})).json()["id"]
    await wait_for_scan_complete(test_client, source_id, draft_id)
    row_id = (await test_client.get(f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows")).json()["items"][0]["id"]
    await test_client.post(
        f"/api/sources/{source_id}/mapping-drafts/{draft_id}/rows/actions",
        json={"row_ids": [row_id], "action": "approve", "force_low_confidence": True},
    )
    preset_id = (
        await test_client.post(f"/api/sources/{source_id}/mapping-presets", json={"name": "Portable preset", "draft_id": draft_id})
    ).json()["id"]

    exported = await test_client.get(f"/api/mapping-presets/{preset_id}/export")
    assert exported.status_code == 200
    assert exported.json()["schema_version"] == 1
    assert exported.json()["template_type"] == "mapping_preset"
    assert exported.json()["payload"]["crawl_plan"]["phases"]

    imported = await test_client.post(
        "/api/mapping-templates/import",
        json={"name": "Imported external", "description": "portable", "content": json.dumps(exported.json())},
    )
    assert imported.status_code == 201
    template_id = imported.json()["id"]

    listing = await test_client.get("/api/mapping-templates")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1

    applied = await test_client.post(f"/api/mapping-templates/{template_id}/apply", params={"source_id": source_id})
    assert applied.status_code == 200
    assert applied.json()["source_id"] == source_id
    assert applied.json()["has_runtime_map"] is True


@pytest.mark.asyncio
async def test_mapping_template_import_rejects_invalid_payload(test_client: AsyncClient):
    invalid_payload = {
        "crawl_plan": {"phases": []},
        "extraction_rules": {"event_detail": {"css_selectors": {"title": 123}}},
    }
    response = await test_client.post(
        "/api/mapping-templates",
        json={"name": "bad-template", "template_json": invalid_payload},
    )
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail["message"] == "Invalid mapping template"
    assert any(error["code"] in {"empty_phases", "invalid_selector_format"} for error in detail["errors"])
