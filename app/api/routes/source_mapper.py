import json

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import (
    MappingDraftCreateRequest,
    MappingDraftSummary,
    MappingPageTypeResponse,
    MappingPreviewRequest,
    MappingPreviewResponse,
    MappingRowActionRequest,
    MappingRowResponse,
    MappingRowUpdateRequest,
    MappingVersionDiffSummary,
    MappingVersionListItem,
    MappingVersionPublishResponse,
)
from app.db import crud
from app.db.models import SourceMappingSample

router = APIRouter(prefix="/sources/{source_id}/mapping-drafts", tags=["source-mapper"])
logger = structlog.get_logger()
LOW_CONFIDENCE_THRESHOLD = 0.65


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

    # Minimal seed-safe defaults so the matrix and preview are immediately usable.
    page_types = await crud.list_source_mapping_page_types(db, draft.id)
    rows = await crud.list_source_mapping_rows(db, source_id, draft.id, skip=0, limit=2000)
    if not page_types and not rows:
        page_type = await crud.create_source_mapping_page_type(
            db,
            draft.id,
            key="generic_detail",
            label="Generic Detail",
            sample_count=1,
            confidence_score=0.55,
        )
        sample = await crud.create_source_mapping_sample(
            db,
            draft.id,
            page_type_id=page_type.id,
            url=source.url,
            title=source.name,
            html_snapshot=None,
        )
        await crud.create_source_mapping_row(
            db,
            draft.id,
            page_type_id=page_type.id,
            selector="title",
            sample_value=source.name or source.url,
            destination_entity="event",
            destination_field="title",
            confidence_score=0.52,
        )
        page_types = [page_type]
        rows = await crud.list_source_mapping_rows(db, source_id, draft.id, skip=0, limit=2000)

    await crud.create_audit_action(
        db,
        action_type="mapping_draft_created",
        user_id="admin",
        source_id=source_id,
        details={"draft_id": draft.id, "scan_mode": body.scan_mode},
    )
    approved_count = sum(1 for row in rows if row.status == "approved")
    needs_review_count = sum(1 for row in rows if row.status in {"proposed", "needs_review"})
    changed_count = sum(1 for row in rows if row.status == "changed_from_published")
    return MappingDraftSummary(
        **MappingDraftSummary.model_validate(draft).model_dump(),
        page_type_count=len(page_types),
        mapping_count=len(rows),
        approved_count=approved_count,
        needs_review_count=needs_review_count,
        changed_from_published_count=changed_count,
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
    approved_count = sum(1 for row in rows if row.status == "approved")
    needs_review_count = sum(1 for row in rows if row.status in {"proposed", "needs_review"})
    changed_count = sum(1 for row in rows if row.status == "changed_from_published")
    return MappingDraftSummary(
        **MappingDraftSummary.model_validate(draft).model_dump(),
        page_type_count=len(page_types),
        mapping_count=len(rows),
        approved_count=approved_count,
        needs_review_count=needs_review_count,
        changed_from_published_count=changed_count,
    )


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
            if row_id in row_map and float(row_map[row_id].confidence_score or 0.0) < LOW_CONFIDENCE_THRESHOLD
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
    sample = None
    if body.sample_page_id == "default":
        draft_samples = await db.execute(select(SourceMappingSample).where(SourceMappingSample.mapping_version_id == draft_id))
        sample = draft_samples.scalars().first()
    else:
        sample = await crud.get_source_mapping_sample(db, body.sample_page_id)
    if sample is None or sample.mapping_version_id != draft_id:
        raise HTTPException(status_code=404, detail="Sample page not found")

    rows = await crud.list_source_mapping_rows(db, source_id, draft_id, skip=0, limit=500)
    extractions = []
    record_preview: dict[str, str] = {}
    category_preview: dict[str, list[str]] = {}
    warnings: list[str] = []
    for row in rows:
        normalized = (row.sample_value or "").strip() or None
        if row.status == "rejected" or not row.is_enabled:
            continue
        warning = None
        if normalized is None:
            warning = "Empty sample value"
        elif float(row.confidence_score or 0.0) < LOW_CONFIDENCE_THRESHOLD:
            warning = "Low confidence mapping - moderation required"
            warnings.append(f"Low confidence extraction for {row.destination_entity}.{row.destination_field}")
        extractions.append(
            {
                "mapping_row_id": row.id,
                "source_selector": row.selector,
                "raw_value": row.sample_value,
                "normalized_value": normalized,
                "destination_entity": row.destination_entity,
                "destination_field": row.destination_field,
                "category_target": row.category_target,
                "confidence_score": row.confidence_score,
                "warning": warning,
            }
        )
        if normalized is not None:
            record_preview[row.destination_field] = normalized
        if row.category_target:
            category_preview.setdefault(row.destination_entity, [])
            if row.category_target not in category_preview[row.destination_entity]:
                category_preview[row.destination_entity].append(row.category_target)

    sample_run = await crud.create_source_mapping_sample_run(
        db,
        draft_id,
        sample_count=1,
        created_by="admin",
        summary={"sample_page_id": body.sample_page_id, "extraction_count": len(extractions)},
    )
    await crud.create_source_mapping_sample_result(
        db,
        sample_run.id,
        sample_id=sample.id,
        record_preview={"record_preview": record_preview, "extractions": extractions},
    )

    page_type_key = sample.page_type.key if sample.page_type else None
    source_snippet = None
    if sample.html_snapshot:
        source_snippet = sample.html_snapshot[:400]
    elif sample.title:
        source_snippet = sample.title[:400]

    return MappingPreviewResponse(
        sample_page_id=sample.id,
        page_url=sample.url,
        page_type_key=page_type_key,
        extractions=extractions,
        record_preview=record_preview,
        source_snippet=source_snippet,
        category_preview=category_preview,
        warnings=warnings,
    )


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
    return MappingVersionPublishResponse(
        id=published.id,
        source_id=published.source_id,
        status=published.status,
        published_at=published.published_at,
        published_by=published.published_by,
    )


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
