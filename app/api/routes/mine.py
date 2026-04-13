import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_ai_client, get_db
from app.api.schemas import (
    JobSummary,
    MineStartRequest,
    MineStartResponse,
    MineStatusProgress,
    MineStatusResponse,
)
from app.config import settings
from app.db import crud

router = APIRouter(prefix="/mine", tags=["mining"])

_WORKER_ONLY_MSG = (
    "Mining tasks cannot run on Vercel serverless. "
    "Deploy a dedicated worker process and point it at the same database."
)


@router.post("/{source_id}/start", response_model=MineStartResponse, status_code=202)
async def start_mining(
    source_id: str,
    body: MineStartRequest | None = None,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    if settings.environment == "production":
        raise HTTPException(status_code=503, detail=_WORKER_ONLY_MSG)
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db,
        source_id=source_id,
        job_type="map_site",
        payload=body.model_dump() if body else {},
    )

    # Run pipeline in background
    async def run_pipeline():
        from app.db.database import AsyncSessionLocal
        from app.pipeline.runner import PipelineRunner

        async with AsyncSessionLocal() as bg_db:
            try:
                ai_client = get_ai_client()
                runner = PipelineRunner(db=bg_db, ai_client=ai_client)
                await runner.run_full_pipeline(source_id)
                await bg_db.commit()
            except Exception:
                await bg_db.rollback()

    background_tasks.add_task(run_pipeline)

    return MineStartResponse(
        job_id=job.id,
        source_id=source_id,
        status="pending",
        message="Mining pipeline started",
    )


@router.post("/{source_id}/map")
async def map_site(source_id: str, db: AsyncSession = Depends(get_db)):
    if settings.environment == "production":
        raise HTTPException(status_code=503, detail=_WORKER_ONLY_MSG)
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    from app.ai.client import OpenAIClient
    from app.crawler.site_mapper import map_site as do_map_site

    ai_client = get_ai_client()
    site_map = await do_map_site(source.url, ai_client=ai_client)

    import json

    site_map_data = {
        "root_url": site_map.root_url,
        "platform": site_map.platform,
        "sections": [
            {
                "name": s.name,
                "url": s.url,
                "content_type": s.content_type,
                "pagination_type": s.pagination_type,
                "index_pattern": s.index_pattern,
                "confidence": s.confidence,
            }
            for s in site_map.sections
        ],
    }
    await crud.update_source(db, source_id, site_map=json.dumps(site_map_data))
    return {"source_id": source_id, "site_map": site_map_data}


@router.post("/{source_id}/crawl", status_code=202)
async def crawl_source(
    source_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    if settings.environment == "production":
        raise HTTPException(status_code=503, detail=_WORKER_ONLY_MSG)
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db, source_id=source_id, job_type="crawl_section", payload={}
    )

    async def run_crawl():
        from app.db.database import AsyncSessionLocal
        from app.pipeline.runner import PipelineRunner

        async with AsyncSessionLocal() as bg_db:
            try:
                ai_client = get_ai_client()
                runner = PipelineRunner(db=bg_db, ai_client=ai_client)
                await runner.run_crawl(source_id)
                await bg_db.commit()
            except Exception:
                await bg_db.rollback()

    background_tasks.add_task(run_crawl)
    return {"job_id": job.id, "status": "pending"}


@router.post("/{source_id}/extract", status_code=202)
async def extract_source(
    source_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    if settings.environment == "production":
        raise HTTPException(status_code=503, detail=_WORKER_ONLY_MSG)
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(
        db, source_id=source_id, job_type="extract_page", payload={}
    )

    async def run_extract():
        from app.db.database import AsyncSessionLocal
        from app.pipeline.runner import PipelineRunner

        async with AsyncSessionLocal() as bg_db:
            try:
                ai_client = get_ai_client()
                runner = PipelineRunner(db=bg_db, ai_client=ai_client)
                await runner.run_extract(source_id)
                await bg_db.commit()
            except Exception:
                await bg_db.rollback()

    background_tasks.add_task(run_extract)
    return {"job_id": job.id, "status": "pending"}


@router.post("/{source_id}/pause")
async def pause_mining(source_id: str, db: AsyncSession = Depends(get_db)):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await crud.update_source(db, source_id, status="paused")
    return {"source_id": source_id, "status": "paused"}


@router.post("/{source_id}/resume", status_code=202)
async def resume_mining(
    source_id: str,
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: AsyncSession = Depends(get_db),
):
    if settings.environment == "production":
        raise HTTPException(status_code=503, detail=_WORKER_ONLY_MSG)
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    job = await crud.create_job(db, source_id=source_id, job_type="map_site", payload={})

    async def run_pipeline():
        from app.db.database import AsyncSessionLocal
        from app.pipeline.runner import PipelineRunner

        async with AsyncSessionLocal() as bg_db:
            try:
                ai_client = get_ai_client()
                runner = PipelineRunner(db=bg_db, ai_client=ai_client)
                await runner.run_full_pipeline(source_id)
                await bg_db.commit()
            except Exception:
                await bg_db.rollback()

    background_tasks.add_task(run_pipeline)
    return {"job_id": job.id, "source_id": source_id, "status": "pending"}


@router.get("/{source_id}/status", response_model=MineStatusResponse)
async def get_mining_status(source_id: str, db: AsyncSession = Depends(get_db)):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")

    jobs = await crud.list_jobs(db, source_id=source_id, status="running")
    current_job = None
    if jobs:
        current_job = JobSummary.model_validate(jobs[0])

    pages_crawled = await crud.count_pages(db, source_id=source_id, status="fetched")
    records_extracted = await crud.count_records(db, source_id=source_id)
    total_pages = source.total_pages or 1
    percent = min(int((pages_crawled / total_pages) * 100), 100) if total_pages > 0 else 0

    progress = MineStatusProgress(
        pages_crawled=pages_crawled,
        pages_total_estimated=total_pages,
        records_extracted=records_extracted,
        percent_complete=percent,
    )

    return MineStatusResponse(
        source_id=source_id,
        status=source.status,
        current_job=current_job,
        progress=progress,
    )
