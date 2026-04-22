import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import (
    MappingDraftCreateRequest,
    MappingDraftSummary,
    MappingPageTypeResponse,
    MappingPreviewRequest,
    MappingPreviewResponse,
    MappingSampleRunRequest,
    MappingSampleRunResponse,
    MappingSampleRunResultItem,
    MappingSampleRunResultResponse,
    MappingSampleRunResultUpdateRequest,
    MappingScanResponse,
    MappingRowActionRequest,
    MappingRowResponse,
    MappingRowUpdateRequest,
    MappingVersionDiffSummary,
    MappingVersionListItem,
    MappingVersionPublishResponse,
)
from app.config import is_serverless_environment, settings
from app.db import crud
from app.queue import QueueUnavailableError, get_default_queue
from app.source_mapper.service import SourceMapperService

router = APIRouter(prefix="/sources/{source_id}/mapping-drafts", tags=["source-mapper"])
logger = structlog.get_logger()
LOW_CONFIDENCE_THRESHOLD = 0.65
MAPPING_SCAN_JOB_TIMEOUT_SECONDS = 900


def _enqueue_mapping_scan_job(source_id: str, draft_id: str) -> str:
    rq_job = get_default_queue().enqueue(
        "app.source_mapper.service.process_mapping_scan_job",
        source_id,
        draft_id,
        job_timeout=MAPPING_SCAN_JOB_TIMEOUT_SECONDS,
    )
    return rq_job.id


async def _dispatch_mapping_scan(db: AsyncSession, source, draft) -> tuple[str, str]:
    run_inline = not is_serverless_environment() and settings.environment in {"development", "docker", "test"}
    if run_inline:
        mapper = SourceMapperService(db)
        result = await mapper.run_scan(source, draft)
        return str(result.get("scan_status", draft.scan_status or "queued")), f"inline-{draft.id}"
    rq_job_id = _enqueue_mapping_scan_job(source.id, draft.id)
    return "queued", rq_job_id


def _confidence_band(score: float) -> str:
    if score >= 0.8:
        return "HIGH"
    if score >= LOW_CONFIDENCE_THRESHOLD:
        return "MEDIUM"
    return "LOW"


async def _get_draft_or_404(db: AsyncSession, source_id: str, draft_id: str):
    draft = await crud.get_source_mapping_version(db, source_id, draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Mapping draft not found")
    return draft


def _serialize_row(row) -> MappingRowResponse:
    transforms = []
    rationale = []
    if row.transforms_json:
        try:
            transforms = json.loads(row.transforms_json)
        except (TypeError, json.JSONDecodeError):
            transforms = []
    if row.confidence_reasons_json:
        try:
            rationale = json.loads(row.confidence_reasons_json)
        except (TypeError, json.JSONDecodeError):
            rationale = []
    payload = MappingRowResponse.model_validate(row).model_dump()
    payload["transforms"] = transforms
    payload["rationale"] = rationale
    payload["confidence_band"] = _confidence_band(float(row.confidence_score or 0.0))
    payload["low_confidence_blocked"] = bool(
        payload["confidence_band"] == "LOW" and row.status in {"proposed", "needs_review"}
    )
    return MappingRowResponse(**payload)


def _draft_progress(draft) -> tuple[int, str | None]:
    try:
        summary = json.loads(draft.summary_json or "{}")
    except (TypeError, json.JSONDecodeError):
        summary = {}
    progress = int(summary.get("progress_percent", 0) or 0)
    stage = summary.get("stage")
    return progress, stage


def _serialize_draft_summary(draft, page_types: list, rows: list) -> MappingDraftSummary:
    approved_count = sum(1 for row in rows if row.status == "approved")
    needs_review_count = sum(1 for row in rows if row.status in {"proposed", "needs_review"})
    changed_count = sum(1 for row in rows if row.status == "changed_from_published")
    scan_progress_percent, scan_stage = _draft_progress(draft)

    payload = MappingDraftSummary.model_validate(draft).model_dump(
        exclude={
            "page_type_count",
            "mapping_count",
            "approved_count",
            "needs_review_count",
            "changed_from_published_count",
            "scan_progress_percent",
            "scan_stage",
        }
    )
    payload.update(
        page_type_count=len(page_types),
        mapping_count=len(rows),
        approved_count=approved_count,
        needs_review_count=needs_review_count,
        changed_from_published_count=changed_count,
        scan_progress_percent=scan_progress_percent,
        scan_stage=scan_stage,
    )
    return MappingDraftSummary(**payload)


def _deserialize_record_preview(raw_json: str | None) -> dict:
    try:
        return json.loads(raw_json or "{}")
    except (TypeError, json.JSONDecodeError):
        return {}


def _serialize_sample_result(result) -> MappingSampleRunResultItem:
    return MappingSampleRunResultItem(
        id=result.id,
        sample_run_id=result.sample_run_id,
        sample_id=result.sample_id,
        review_status=result.review_status,
        review_notes=result.review_notes,
        record_preview=_deserialize_record_preview(result.record_preview_json),
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


def _serialize_version_publish_response(version) -> MappingVersionPublishResponse:
    return MappingVersionPublishResponse(
        id=version.id,
        source_id=version.source_id,
        status=version.status,
        published_at=version.published_at,
        published_by=version.published_by,
    )


@router.post("", response_model=MappingDraftSummary, status_code=201)
async def create_mapping_draft(
    source_id: str,
    body: MappingDraftCreateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    options = body.model_dump()
    if body.scan_mode == "edit_published":
        try:
            draft = await crud.clone_published_mapping_to_draft(db, source_id, created_by="admin")
        except ValueError:
            draft = await crud.create_source_mapping_version(db, source_id, scan_options=options, created_by="admin")
    else:
        draft = await crud.create_source_mapping_version(db, source_id, scan_options=options, created_by="admin")

    draft.scan_status = "queued"
    draft.summary_json = json.dumps({"progress_percent": 0, "stage": "queued"})
    await db.commit()
    await db.refresh(draft)

    try:
        status, _ = await _dispatch_mapping_scan(db, source, draft)
        draft.scan_status = status
        await db.commit()
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        if settings.environment in {"development", "docker", "test"}:
            logger.warning(
                "mapping_scan_queue_unavailable_running_inline",
                source_id=source_id,
                draft_id=draft.id,
                error=str(exc),
            )
            mapper = SourceMapperService(db)
            result = await mapper.run_scan(source, draft)
            draft.scan_status = str(result.get("scan_status", draft.scan_status or "completed"))
            await db.commit()
        else:
            logger.error("mapping_scan_enqueue_failed", source_id=source_id, draft_id=draft.id, error=str(exc))
            draft.scan_status = "error"
            draft.summary_json = json.dumps({"progress_percent": 100, "stage": "error"})
            await db.commit()
            raise HTTPException(status_code=503, detail="Failed to queue mapping scan job.") from exc

    page_types = await crud.list_source_mapping_page_types(db, draft.id)
    rows = await crud.list_source_mapping_rows(db, source_id, draft.id, skip=0, limit=2000)

    await crud.create_audit_action(
        db,
        action_type="mapping_draft_created",
        user_id="admin",
        source_id=source_id,
        details={"draft_id": draft.id, "scan_mode": body.scan_mode},
    )
    return _serialize_draft_summary(draft, page_types, rows)


@router.post("/{draft_id}/scan", response_model=MappingScanResponse, status_code=202)
async def start_or_restart_scan(
    source_id: str,
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    draft = await _get_draft_or_404(db, source_id, draft_id)
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    draft.scan_status = "queued"
    draft.summary_json = json.dumps({"progress_percent": 0, "stage": "queued"})
    await db.commit()
    try:
        status, rq_job_id = await _dispatch_mapping_scan(db, source, draft)
    except (QueueUnavailableError, RedisError, OSError, RuntimeError) as exc:
        if settings.environment in {"development", "docker", "test"}:
            logger.warning(
                "mapping_scan_queue_unavailable_running_inline",
                source_id=source_id,
                draft_id=draft_id,
                error=str(exc),
            )
            mapper = SourceMapperService(db)
            result = await mapper.run_scan(source, draft)
            status = str(result.get("scan_status", draft.scan_status or "completed"))
            rq_job_id = f"inline-{draft_id}"
            draft.scan_status = status
            await db.commit()
        else:
            logger.error("mapping_scan_enqueue_failed", source_id=source_id, draft_id=draft_id, error=str(exc))
            draft.scan_status = "error"
            draft.summary_json = json.dumps({"progress_percent": 100, "stage": "error"})
            await db.commit()
            raise HTTPException(status_code=503, detail="Failed to queue mapping scan job.") from exc
    return MappingScanResponse(
        draft_id=draft_id,
        scan_status=status,
        job_id=rq_job_id,
        message="Mapping scan completed." if status == "completed" else "Mapping scan queued.",
    )


@router.get("/{draft_id}", response_model=MappingDraftSummary)
async def get_scan_status_and_results(
    source_id: str,
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    draft = await _get_draft_or_404(db, source_id, draft_id)
    page_types = await crud.list_source_mapping_page_types(db, draft.id)
    rows = await crud.list_source_mapping_rows(db, source_id, draft.id, skip=0, limit=1000)
    return _serialize_draft_summary(draft, page_types, rows)


@router.get("/{draft_id}/rows", response_model=dict)
async def list_proposed_mappings(
    source_id: str,
    draft_id: str,
    page_type_key: str | None = None,
    status: str | None = None,
    destination_entity: str | None = None,
    min_confidence: float | None = Query(default=None, ge=0.0, le=1.0),
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    await _get_draft_or_404(db, source_id, draft_id)
    rows = await crud.list_source_mapping_rows(
        db,
        source_id,
        draft_id,
        page_type_key=page_type_key,
        status=status,
        destination_entity=destination_entity,
        min_confidence=min_confidence,
        skip=skip,
        limit=limit,
    )
    items = [_serialize_row(row).model_dump() for row in rows]
    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.patch("/{draft_id}/rows/{row_id}", response_model=MappingRowResponse)
async def update_mapping_row(
    source_id: str,
    draft_id: str,
    row_id: str,
    body: MappingRowUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _get_draft_or_404(db, source_id, draft_id)
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    try:
        row = await crud.update_source_mapping_row(db, source_id, draft_id, row_id, **updates)
    except ValueError as exc:
        message = str(exc)
        if "Invalid destination" in message:
            raise HTTPException(status_code=400, detail=message) from exc
        raise HTTPException(status_code=404, detail=message) from exc
    await crud.create_audit_action(
        db,
        action_type="mapping_row_updated",
        user_id="admin",
        source_id=source_id,
        record_id=row_id,
        details={"draft_id": draft_id, "updates": updates},
    )
    return _serialize_row(row)


@router.post("/{draft_id}/rows/actions", response_model=dict)
async def approve_or_reject_rows(
    source_id: str,
    draft_id: str,
    body: MappingRowActionRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _get_draft_or_404(db, source_id, draft_id)
    action_map: dict[str, dict[str, object]] = {
        "approve": {"status": "approved"},
        "reject": {"status": "rejected"},
        "ignore": {"status": "ignored"},
        "disable": {"is_enabled": False},
        "enable": {"is_enabled": True},
        "needs_review": {"status": "needs_review"},
    }
    if body.action == "move_destination":
        if not body.destination_entity or not body.destination_field:
            raise HTTPException(status_code=400, detail="destination_entity and destination_field are required")
        updated = 0
        for row_id in body.row_ids:
            row = await crud.update_source_mapping_row(
                db,
                source_id,
                draft_id,
                row_id,
                destination_entity=body.destination_entity,
                destination_field=body.destination_field,
                status="needs_review",
            )
            if row is not None:
                updated += 1
        await crud.create_audit_action(
            db,
            action_type="mapping_rows_bulk_action",
            user_id="admin",
            source_id=source_id,
            affected_record_ids=body.row_ids,
            details={
                "draft_id": draft_id,
                "action": body.action,
                "destination_entity": body.destination_entity,
                "destination_field": body.destination_field,
            },
        )
        return {"updated": updated, "action": body.action}

    config = action_map.get(body.action)
    if config is None:
        raise HTTPException(status_code=400, detail="Unsupported action")
    if body.action == "approve" and not body.force_low_confidence:
        rows = await crud.list_source_mapping_rows(db, source_id, draft_id, skip=0, limit=max(len(body.row_ids), 1_000))
        row_map = {row.id: row for row in rows}
        low_confidence = [
            row_id for row_id in body.row_ids
            if (
                row_id in row_map
                and float(row_map[row_id].confidence_score or 0.0) < LOW_CONFIDENCE_THRESHOLD
                and row_map[row_id].status == "proposed"
            )
        ]
        if low_confidence:
            raise HTTPException(
                status_code=409,
                detail=f"Low-confidence mappings require force approval: {', '.join(low_confidence)}",
            )
    updated = await crud.set_source_mapping_rows_status(
        db,
        source_id,
        draft_id,
        body.row_ids,
        status=config.get("status"),
        is_enabled=config.get("is_enabled"),
    )
    await crud.create_audit_action(
        db,
        action_type="mapping_rows_bulk_action",
        user_id="admin",
        source_id=source_id,
        affected_record_ids=body.row_ids,
        details={"draft_id": draft_id, "action": body.action, "updated": updated},
    )
    return {"updated": updated, "action": body.action}


@router.get("/{draft_id}/page-types", response_model=dict)
async def list_page_types(
    source_id: str,
    draft_id: str,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    await _get_draft_or_404(db, source_id, draft_id)
    page_types = await crud.list_source_mapping_page_types(db, draft_id)
    items = [MappingPageTypeResponse.model_validate(page_type).model_dump() for page_type in page_types[skip: skip + limit]]
    return {"items": items, "total": len(page_types), "skip": skip, "limit": limit}


@router.post("/{draft_id}/preview", response_model=MappingPreviewResponse)
async def generate_preview(
    source_id: str,
    draft_id: str,
    body: MappingPreviewRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    await _get_draft_or_404(db, source_id, draft_id)
    mapper = SourceMapperService(db)
    try:
        preview = await mapper.generate_preview(source_id, draft_id, body.sample_page_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MappingPreviewResponse(**preview)


@router.post("/{draft_id}/sample-run", response_model=MappingSampleRunResponse, status_code=202)
async def start_sample_run(
    source_id: str,
    draft_id: str,
    body: MappingSampleRunRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    await _get_draft_or_404(db, source_id, draft_id)
    mapper = SourceMapperService(db)
    result = await mapper.run_sample_review(
        source_id,
        draft_id,
        sample_count=body.sample_count,
        page_type_keys=body.page_type_keys or None,
    )
    return MappingSampleRunResponse(**result)


@router.get("/{draft_id}/sample-run/{sample_run_id}", response_model=MappingSampleRunResultResponse)
async def get_sample_run_results(
    source_id: str,
    draft_id: str,
    sample_run_id: str,
    review_status: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    sample_run = await crud.get_source_mapping_sample_run(db, source_id, draft_id, sample_run_id)
    if sample_run is None:
        raise HTTPException(status_code=404, detail="Sample run not found")
    results = await crud.list_source_mapping_sample_results(db, sample_run_id, review_status=review_status)
    items = [_serialize_sample_result(item) for item in results]
    return MappingSampleRunResultResponse(sample_run_id=sample_run_id, status=sample_run.status, items=items)


@router.patch("/{draft_id}/sample-run/{sample_run_id}/results/{result_id}", response_model=MappingSampleRunResultItem)
async def update_sample_run_result(
    source_id: str,
    draft_id: str,
    sample_run_id: str,
    result_id: str,
    body: MappingSampleRunResultUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields provided for update")
    try:
        result = await crud.update_source_mapping_sample_result(
            db,
            source_id,
            draft_id,
            sample_run_id,
            result_id,
            review_status=updates.get("review_status"),
            review_notes=updates.get("review_notes"),
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await crud.create_audit_action(
        db,
        action_type="mapping_sample_result_updated",
        user_id="admin",
        source_id=source_id,
        details={
            "draft_id": draft_id,
            "sample_run_id": sample_run_id,
            "result_id": result_id,
            "updates": updates,
        },
    )
    return _serialize_sample_result(result)


@router.get("", response_model=dict)
async def list_mapping_versions(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    versions = await crud.list_source_mapping_versions(db, source_id)
    items = [MappingVersionListItem.model_validate(version).model_dump() for version in versions]
    return {"items": items, "total": len(items), "skip": 0, "limit": len(items)}


@router.post("/{draft_id}/publish", response_model=MappingVersionPublishResponse)
async def publish_mapping_draft(
    source_id: str,
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    try:
        published = await crud.publish_source_mapping_version(db, source_id, draft_id, published_by="admin")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await crud.create_audit_action(
        db,
        action_type="mapping_draft_published",
        user_id="admin",
        source_id=source_id,
        record_id=draft_id,
        details={"draft_id": draft_id, "status": published.status},
    )
    return _serialize_version_publish_response(published)


@router.get("/{draft_id}/diff", response_model=MappingVersionDiffSummary)
async def get_mapping_diff(
    source_id: str,
    draft_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    draft = await _get_draft_or_404(db, source_id, draft_id)
    source = await crud.get_source(db, source_id)
    if source is None or source.active_mapping_version_id is None or source.active_mapping_version_id == draft.id:
        rows = await crud.list_source_mapping_rows(db, source_id, draft_id, skip=0, limit=2000)
        return MappingVersionDiffSummary(added=len(rows), removed=0, changed=0, unchanged=0)

    draft_rows = await crud.list_source_mapping_rows(db, source_id, draft_id, skip=0, limit=2000)
    published_rows = await crud.list_source_mapping_rows(db, source_id, source.active_mapping_version_id, skip=0, limit=2000)
    draft_map = {(r.selector, r.destination_entity, r.destination_field): r for r in draft_rows}
    published_map = {(r.selector, r.destination_entity, r.destination_field): r for r in published_rows}

    added = len([key for key in draft_map if key not in published_map])
    removed = len([key for key in published_map if key not in draft_map])
    changed = 0
    unchanged = 0
    for key in draft_map:
        if key not in published_map:
            continue
        drow = draft_map[key]
        prow = published_map[key]
        if (
            drow.status != prow.status
            or drow.is_enabled != prow.is_enabled
            or drow.category_target != prow.category_target
            or (drow.sample_value or "") != (prow.sample_value or "")
        ):
            changed += 1
        else:
            unchanged += 1
    return MappingVersionDiffSummary(added=added, removed=removed, changed=changed, unchanged=unchanged)


@router.post("/versions/{version_id}/rollback", response_model=MappingVersionPublishResponse)
async def rollback_mapping_version(
    source_id: str,
    version_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    try:
        restored = await crud.rollback_source_mapping_version(db, source_id, version_id, rolled_back_by="admin")
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await crud.create_audit_action(
        db,
        action_type="mapping_version_rolled_back",
        user_id="admin",
        source_id=source_id,
        record_id=version_id,
        details={"active_mapping_version_id": restored.id},
    )
    return _serialize_version_publish_response(restored)
