from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import crud
from tests.conftest import TestSessionLocal
from app.pipeline.runner import _run_pipeline_job_async


@pytest.mark.asyncio
async def test_reclassify_page_enqueues_and_marks_job_queued(
    test_client: AsyncClient,
    db_session: AsyncSession,
):
    source = await crud.create_source(db_session, url="https://page-dispatch.com")
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://page-dispatch.com/a",
        original_url="https://page-dispatch.com/a",
        html="<html><body>hi</body></html>",
        status="fetched",
    )

    with patch("app.api.routes.pages._enqueue_page_job", return_value="rq-page-1"):
        resp = await test_client.post(f"/api/pages/{page.id}/reclassify")

    assert resp.status_code == 202
    payload = resp.json()
    assert payload["status"] == "queued"
    job = await crud.get_job(db_session, payload["job_id"])
    assert job is not None
    assert job.status == "queued"


@pytest.mark.asyncio
async def test_reextract_page_enqueue_failure_marks_job_failed(
    test_client: AsyncClient,
    db_session: AsyncSession,
):
    source = await crud.create_source(db_session, url="https://page-dispatch-fail.com")
    page = await crud.create_page(
        db_session,
        source_id=source.id,
        url="https://page-dispatch-fail.com/a",
        original_url="https://page-dispatch-fail.com/a",
        html="<html><body>hi</body></html>",
        status="classified",
    )

    with patch("app.api.routes.pages._enqueue_page_job", side_effect=RuntimeError("queue down")):
        resp = await test_client.post(f"/api/pages/{page.id}/reextract")

    assert resp.status_code == 503
    jobs = await crud.list_jobs(db_session, source_id=source.id, status="failed")
    assert len(jobs) == 1


@pytest.mark.asyncio
async def test_runner_supports_reclassify_and_reextract_job_types(db_session: AsyncSession):
    source = await crud.create_source(db_session, url="https://runner-jobs.com")
    reclassify_job = await crud.create_job(
        db_session,
        source_id=source.id,
        job_type="reclassify_page",
        payload={"page_id": "p-1"},
    )
    reextract_job = await crud.create_job(
        db_session,
        source_id=source.id,
        job_type="reextract_page",
        payload={"page_id": "p-2"},
    )

    with (
        patch("app.pipeline.runner.AsyncSessionLocal", return_value=TestSessionLocal()),
        patch("app.pipeline.runner.worker_log_processor.start", AsyncMock()),
        patch("app.pipeline.runner.worker_log_processor.stop", AsyncMock()),
        patch("app.pipeline.runner.PipelineRunner.run_reclassify_page", AsyncMock(return_value={"status": "classified"})),
        patch("app.pipeline.runner.PipelineRunner.run_reextract_page", AsyncMock(return_value={"status": "extracted"})),
    ):
        await _run_pipeline_job_async(reclassify_job.id, source.id, "reclassify_page", {"page_id": "p-1"})
        await _run_pipeline_job_async(reextract_job.id, source.id, "reextract_page", {"page_id": "p-2"})

    reclassify_refreshed = await crud.get_job(db_session, reclassify_job.id)
    reextract_refreshed = await crud.get_job(db_session, reextract_job.id)
    assert reclassify_refreshed is not None and reclassify_refreshed.status == "done"
    assert reextract_refreshed is not None and reextract_refreshed.status == "done"
