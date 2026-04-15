import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud


@pytest.mark.asyncio
async def test_multi_source_config_and_filter(test_client: AsyncClient):
    response = await test_client.post(
        "/api/sources",
        json={
            "url": "https://source-a.example",
            "name": "Source A",
            "enabled": False,
            "max_depth": 4,
            "crawl_hints": {"seed": ["/artists"]},
            "extraction_rules": {"artists": {"required": ["title"]}},
        },
    )
    assert response.status_code == 201
    created = response.json()
    assert created["enabled"] is False
    assert created["max_depth"] == 4

    enabled_list = await test_client.get("/api/sources", params={"enabled": True})
    assert enabled_list.status_code == 200
    assert all(item["enabled"] for item in enabled_list.json()["items"])


@pytest.mark.asyncio
async def test_jobs_queue_list_retry_cancel(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://jobs-source.example")
    job = await crud.create_job(
        db_session,
        source_id=source.id,
        job_type="crawl_job",
        payload={"depth": 2},
    )
    await crud.update_job_status(db_session, job.id, "failed")

    listing = await test_client.get("/api/jobs")
    assert listing.status_code == 200
    assert any(item["id"] == job.id for item in listing.json()["items"])

    retry_resp = await test_client.post(f"/api/jobs/{job.id}/retry")
    assert retry_resp.status_code == 200
    assert retry_resp.json()["status"] == "pending"

    cancel_resp = await test_client.post(f"/api/jobs/{job.id}/cancel")
    assert cancel_resp.status_code == 200
    assert cancel_resp.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_review_queues(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://review-queues.example")
    left = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Artist Left",
        has_conflicts=True,
        completeness_score=20,
    )
    right = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Artist Right",
        completeness_score=30,
    )
    await crud.upsert_duplicate_review(
        db_session,
        left_record_id=left.id,
        right_record_id=right.id,
        similarity_score=92,
        reason="name overlap",
    )

    conflict_queue = await test_client.get("/api/queues/review", params={"type": "conflicts"})
    assert conflict_queue.status_code == 200
    assert conflict_queue.json()["total"] >= 1

    duplicates_queue = await test_client.get("/api/queues/review", params={"type": "duplicates"})
    assert duplicates_queue.status_code == 200
    assert duplicates_queue.json()["total"] >= 1


@pytest.mark.asyncio
async def test_schedule_and_rbac(test_client: AsyncClient, db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://schedule-source.example")

    forbidden = await test_client.post(
        "/api/schedule",
        headers={"x-role": "viewer"},
        json={"job_type": "crawl_job", "cron": "0 * * * *", "source_id": source.id},
    )
    assert forbidden.status_code == 403

    created = await test_client.post(
        "/api/schedule",
        headers={"x-role": "admin"},
        json={"job_type": "export_job", "cron": "0 2 * * *", "source_id": source.id},
    )
    assert created.status_code == 200

    listing = await test_client.get("/api/schedule")
    assert listing.status_code == 200
    assert listing.json()["total"] >= 1


@pytest.mark.asyncio
async def test_metrics_history_endpoint(test_client: AsyncClient):
    response = await test_client.get("/api/metrics/history", params={"days": 5})
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 5
    assert "completeness_avg" in data["items"][0]


@pytest.mark.asyncio
async def test_merge_rollback_restores_secondary_record(
    test_client: AsyncClient,
    db_session: AsyncSession,
):
    source = await crud.create_source(db_session, url="https://merge-rollback.example")
    primary = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Primary Artist",
        bio="Primary bio",
        source_url="https://merge-rollback.example/p",
    )
    secondary = await crud.create_record(
        db_session,
        source_id=source.id,
        record_type="artist",
        title="Secondary Artist",
        bio="Secondary bio",
        source_url="https://merge-rollback.example/s",
    )
    await crud.upsert_entity_relationship(
        db_session,
        source_id=source.id,
        from_record_id=secondary.id,
        to_record_id=primary.id,
        relationship_type="related_artist",
    )

    merge_response = await test_client.post(
        "/api/merge/artists",
        json={"primary_id": primary.id, "secondary_id": secondary.id},
    )
    assert merge_response.status_code == 200
    merge_id = merge_response.json()["merge_id"]

    rollback_response = await test_client.post(f"/api/merge/{merge_id}/rollback")
    assert rollback_response.status_code == 200
    assert rollback_response.json()["status"] == "rolled_back"

    restored_secondary = await crud.get_record(db_session, secondary.id)
    assert restored_secondary is not None
    assert restored_secondary.title == "Secondary Artist"
