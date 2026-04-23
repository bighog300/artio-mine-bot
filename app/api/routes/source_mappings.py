import json

from fastapi import APIRouter, Depends, HTTPException
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import (
    MappingCrawlTriggerResponse,
    MappingRefreshEligibilityResponse,
    MappingRefreshTriggerResponse,
    MappingFamilyRuleResponse,
    MappingSuggestionDraftRequest,
    MappingSuggestionResponse,
    MappingSuggestionUpdateRequest,
)
from app.db import crud
from app.queue import QueueUnavailableError, get_default_queue
from app.source_mapper.mapping_suggestion_service import MappingSuggestionService

router = APIRouter(prefix="/sources/{source_id}/mappings", tags=["source-mappings"])


def serialize_mapping_suggestion(version) -> MappingSuggestionResponse:
    mapping_json = json.loads(version.mapping_json or "{}")
    summary = json.loads(version.summary_json or "{}") if version.summary_json else {}
    family_rules = [MappingFamilyRuleResponse(**rule) for rule in mapping_json.get("family_rules", [])]
    return MappingSuggestionResponse(
        id=version.id,
        source_id=version.source_id,
        based_on_profile_id=version.based_on_profile_id,
        version_number=version.version_number,
        status=version.status,
        is_active=bool(version.is_active),
        approved_at=version.approved_at,
        approved_by=version.approved_by,
        superseded_at=version.superseded_at,
        created_at=version.created_at,
        family_rules=family_rules,
        diagnostics=summary,
    )


@router.post("/draft", response_model=MappingSuggestionResponse, status_code=201)
async def create_mapping_draft_from_profile(
    source_id: str,
    body: MappingSuggestionDraftRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    profile = await crud.get_source_profile(db, source_id, body.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    service = MappingSuggestionService(db)
    version = await service.generate_draft(source_id, body.profile_id)
    return serialize_mapping_suggestion(version)


@router.patch("/{mapping_id}", response_model=MappingSuggestionResponse)
async def update_mapping_draft(
    source_id: str,
    mapping_id: str,
    body: MappingSuggestionUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    try:
        version = await crud.update_mapping_suggestion_draft_family_rules(
            db,
            source_id=source_id,
            mapping_id=mapping_id,
            family_updates=[rule.model_dump(exclude_unset=True) for rule in body.family_rules],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_mapping_suggestion(version)


@router.get("/{mapping_id}", response_model=MappingSuggestionResponse)
async def get_mapping_draft(
    source_id: str,
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    version = await crud.get_mapping_suggestion_version(db, source_id=source_id, mapping_id=mapping_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Mapping version not found")
    return serialize_mapping_suggestion(version)


@router.post("/{mapping_id}/approve", response_model=MappingSuggestionResponse)
async def approve_mapping_draft(
    source_id: str,
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    try:
        version = await crud.approve_mapping_suggestion_version(
            db,
            source_id=source_id,
            mapping_id=mapping_id,
            approved_by="admin",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return serialize_mapping_suggestion(version)


@router.post("/{mapping_id}/crawl", response_model=MappingCrawlTriggerResponse)
async def trigger_crawl_from_approved_mapping(
    source_id: str,
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    version = await crud.get_mapping_suggestion_draft(db, source_id=source_id, mapping_id=mapping_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Mapping version not found")
    if version.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved mappings can trigger crawl execution")

    payload = {"mapping_version_id": mapping_id, "trigger": "approved_mapping_manual"}
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        await crud.update_source(db, source_id, status="queued", error_message=None)
        job = await crud.create_job(db, source_id=source_id, job_type="crawl_section", payload=payload)
        await crud.update_job_status(db, job.id, "queued")
        queue_job = get_default_queue().enqueue(
            "app.pipeline.runner.process_pipeline_job",
            job.id,
            source_id,
            "crawl_section",
            payload,
            job_timeout=900,
        )
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"Failed to queue crawl job: {exc}") from exc

    return MappingCrawlTriggerResponse(
        source_id=source_id,
        mapping_id=mapping_id,
        job_id=job.id,
        queue_job_id=queue_job.id,
        status="queued",
        message="Crawl triggered from approved mapping",
    )


@router.get("/{mapping_id}/refresh/eligibility", response_model=MappingRefreshEligibilityResponse)
async def get_refresh_eligibility(
    source_id: str,
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    version = await crud.get_mapping_suggestion_draft(db, source_id=source_id, mapping_id=mapping_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Mapping version not found")
    if version.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved mappings can trigger refresh execution")
    counts = await crud.get_refresh_eligibility_counts(
        db,
        source_id=source_id,
        mapping_version_id=mapping_id,
    )
    return MappingRefreshEligibilityResponse(
        source_id=source_id,
        mapping_id=mapping_id,
        **counts,
    )


@router.post("/{mapping_id}/refresh", response_model=MappingRefreshTriggerResponse)
async def trigger_refresh_from_approved_mapping(
    source_id: str,
    mapping_id: str,
    force: bool = False,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    version = await crud.get_mapping_suggestion_draft(db, source_id=source_id, mapping_id=mapping_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Mapping version not found")
    if version.status != "approved":
        raise HTTPException(status_code=400, detail="Only approved mappings can trigger refresh execution")
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    crawl_run = await crud.create_crawl_run(
        db,
        source_id=source_id,
        seed_url=source.url,
        status="queued",
        mapping_version_id=mapping_id,
    )
    selection = await crud.prepare_refresh_frontier_rows(
        db,
        crawl_run_id=crawl_run.id,
        source_id=source_id,
        mapping_version_id=mapping_id,
        force=force,
    )

    payload = {
        "mapping_version_id": mapping_id,
        "trigger": "approved_mapping_refresh_manual",
        "crawl_run_id": crawl_run.id,
        "force_refresh": force,
    }
    try:
        await crud.update_source(db, source_id, status="queued", error_message=None)
        job = await crud.create_job(db, source_id=source_id, job_type="crawl_refresh", payload=payload)
        await crud.update_job_status(db, job.id, "queued")
        queue_job = get_default_queue().enqueue(
            "app.pipeline.runner.process_pipeline_job",
            job.id,
            source_id,
            "crawl_refresh",
            payload,
            job_timeout=900,
        )
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"Failed to queue refresh job: {exc}") from exc

    return MappingRefreshTriggerResponse(
        source_id=source_id,
        mapping_id=mapping_id,
        crawl_run_id=crawl_run.id,
        job_id=job.id,
        queue_job_id=queue_job.id,
        status="queued",
        selected=int(selection.get("selected", 0)),
        skipped_not_due=int(selection.get("skipped_not_due", 0)),
        message="Refresh crawl triggered from approved mapping",
    )
