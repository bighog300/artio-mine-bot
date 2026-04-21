from types import SimpleNamespace

import pytest


async def _create_source_profile_and_draft(test_client):
    source_resp = await test_client.post("/api/sources", json={"url": "https://phase3-map.test"})
    source_id = source_resp.json()["id"]

    profile_resp = await test_client.post(f"/api/sources/{source_id}/profiles", json={"max_pages": 20})
    profile_id = profile_resp.json()["id"]

    draft_resp = await test_client.post(f"/api/sources/{source_id}/mappings/draft", json={"profile_id": profile_id})
    assert draft_resp.status_code == 201
    return source_id, profile_id, draft_resp.json()


@pytest.mark.asyncio
async def test_draft_mapping_update_and_approved_is_immutable(test_client):
    source_id, _, draft = await _create_source_profile_and_draft(test_client)
    mapping_id = draft["id"]
    family_key = draft["family_rules"][0]["family_key"]

    patch_resp = await test_client.patch(
        f"/api/sources/{source_id}/mappings/{mapping_id}",
        json={"family_rules": [{"family_key": family_key, "page_type": "artist", "include": False}]},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["family_rules"][0]["page_type"] == "artist"
    assert patch_resp.json()["family_rules"][0]["include"] is False

    approve_resp = await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    blocked_patch_resp = await test_client.patch(
        f"/api/sources/{source_id}/mappings/{mapping_id}",
        json={"family_rules": [{"family_key": family_key, "page_type": "listing"}]},
    )
    assert blocked_patch_resp.status_code == 400


@pytest.mark.asyncio
async def test_approve_sets_single_active_mapping_per_source(test_client):
    source_id, profile_id, draft1 = await _create_source_profile_and_draft(test_client)

    draft2_resp = await test_client.post(f"/api/sources/{source_id}/mappings/draft", json={"profile_id": profile_id})
    draft2 = draft2_resp.json()

    approve1 = await test_client.post(f"/api/sources/{source_id}/mappings/{draft1['id']}/approve")
    assert approve1.status_code == 200
    assert approve1.json()["is_active"] is True

    approve2 = await test_client.post(f"/api/sources/{source_id}/mappings/{draft2['id']}/approve")
    assert approve2.status_code == 200
    assert approve2.json()["is_active"] is True

    old_detail = await test_client.get(f"/api/sources/{source_id}/mappings/{draft1['id']}")
    assert old_detail.status_code == 200
    assert old_detail.json()["status"] == "superseded"
    assert old_detail.json()["is_active"] is False


@pytest.mark.asyncio
async def test_crawl_trigger_rejects_draft_and_accepts_approved(test_client, monkeypatch):
    class _FakeQueue:
        def enqueue(self, *_args, **_kwargs):
            return SimpleNamespace(id="rq-job-123")

    monkeypatch.setattr("app.api.routes.source_mappings.get_default_queue", lambda: _FakeQueue())

    source_id, _, draft = await _create_source_profile_and_draft(test_client)
    mapping_id = draft["id"]

    draft_trigger = await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/crawl")
    assert draft_trigger.status_code == 400

    await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/approve")
    approved_trigger = await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/crawl")
    assert approved_trigger.status_code == 200
    payload = approved_trigger.json()
    assert payload["mapping_id"] == mapping_id
    assert payload["queue_job_id"] == "rq-job-123"
    assert payload["job_id"]


@pytest.mark.asyncio
async def test_admin_protection_for_mapping_approval_routes(test_client):
    source_id, _, draft = await _create_source_profile_and_draft(test_client)
    mapping_id = draft["id"]

    key_resp = await test_client.post(
        "/api/keys",
        json={"name": "viewer-only", "permissions": ["read"]},
    )
    viewer_key = key_resp.json()["raw_key"]
    viewer_headers = {"X-Admin-Token": "", "X-API-Key": viewer_key}

    patch_resp = await test_client.patch(
        f"/api/sources/{source_id}/mappings/{mapping_id}",
        headers=viewer_headers,
        json={"family_rules": [{"family_key": draft["family_rules"][0]["family_key"], "page_type": "artist"}]},
    )
    approve_resp = await test_client.post(
        f"/api/sources/{source_id}/mappings/{mapping_id}/approve",
        headers=viewer_headers,
    )
    crawl_resp = await test_client.post(
        f"/api/sources/{source_id}/mappings/{mapping_id}/crawl",
        headers=viewer_headers,
    )

    assert patch_resp.status_code == 403
    assert approve_resp.status_code == 403
    assert crawl_resp.status_code == 403


@pytest.mark.asyncio
async def test_integration_profile_to_draft_edit_approve_trigger(test_client, monkeypatch):
    class _FakeQueue:
        def enqueue(self, *_args, **_kwargs):
            return SimpleNamespace(id="rq-job-integration")

    monkeypatch.setattr("app.api.routes.source_mappings.get_default_queue", lambda: _FakeQueue())

    source_id, _, draft = await _create_source_profile_and_draft(test_client)
    mapping_id = draft["id"]
    family_key = draft["family_rules"][0]["family_key"]

    edit = await test_client.patch(
        f"/api/sources/{source_id}/mappings/{mapping_id}",
        json={"family_rules": [{"family_key": family_key, "freshness_policy": "daily"}]},
    )
    assert edit.status_code == 200

    approve = await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/approve")
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    trigger = await test_client.post(f"/api/sources/{source_id}/mappings/{mapping_id}/crawl")
    assert trigger.status_code == 200
    assert trigger.json()["queue_job_id"] == "rq-job-integration"
