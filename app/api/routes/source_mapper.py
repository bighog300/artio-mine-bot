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
)
from app.db import crud
from app.db.models import SourceMappingSample

router = APIRouter(prefix="/sources/{source_id}/mapping-drafts", tags=["source-mapper"])
logger = structlog.get_logger()


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
    draft = await crud.create_source_mapping_version(db, source_id, scan_options=options, created_by="admin")

    # Minimal seed-safe defaults so the matrix and preview are immediately usable.
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

    return MappingDraftSummary(
        **MappingDraftSummary.model_validate(draft).model_dump(),
        page_type_count=1,
        mapping_count=1,
        approved_count=0,
        needs_review_count=1,
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
    return MappingDraftSummary(
        **MappingDraftSummary.model_validate(draft).model_dump(),
        page_type_count=len(page_types),
        mapping_count=len(rows),
        approved_count=approved_count,
        needs_review_count=needs_review_count,
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
        "disable": {"is_enabled": False},
        "enable": {"is_enabled": True},
        "needs_review": {"status": "needs_review"},
    }
    config = action_map.get(body.action)
    if config is None:
        raise HTTPException(status_code=400, detail="Unsupported action")
    updated = await crud.set_source_mapping_rows_status(
        db,
        source_id,
        draft_id,
        body.row_ids,
        status=config.get("status"),
        is_enabled=config.get("is_enabled"),
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
    for row in rows:
        normalized = (row.sample_value or "").strip() or None
        if row.status == "rejected" or not row.is_enabled:
            continue
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
                "warning": None if normalized else "Empty sample value",
            }
        )
        if normalized is not None:
            record_preview[row.destination_field] = normalized

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
    return MappingPreviewResponse(
        sample_page_id=sample.id,
        page_url=sample.url,
        page_type_key=page_type_key,
        extractions=extractions,
        record_preview=record_preview,
    )
