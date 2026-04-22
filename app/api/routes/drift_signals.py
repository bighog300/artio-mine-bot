import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import (
    DriftFieldsResponse,
    DriftRemapDraftResponse,
    DriftSummaryResponse,
    DriftSignalStatusUpdateRequest,
    MappingDriftSignalListResponse,
    MappingDriftSignalResponse,
)
from app.db import crud
from app.pipeline.drift_detection import DriftDetectionService as ExtractionDriftDetectionService
from app.pipeline.runner import PipelineRunner
from app.source_mapper.drift_detection import DriftDetectionService

router = APIRouter(prefix="/sources/{source_id}/drift-signals", tags=["mapping-drift"])
overview_router = APIRouter(tags=["mapping-drift"])


def _serialize_signal(signal) -> MappingDriftSignalResponse:
    return MappingDriftSignalResponse(
        id=signal.id,
        source_id=signal.source_id,
        mapping_version_id=signal.mapping_version_id,
        page_id=signal.page_id,
        page_url=(signal.sample_urls_json and (json.loads(signal.sample_urls_json or "[]")[0] if json.loads(signal.sample_urls_json or "[]") else None)),
        record_id=signal.record_id,
        field_name=signal.field_name,
        drift_type=signal.drift_type,
        family_key=signal.family_key,
        signal_type=signal.signal_type,
        severity=signal.severity,
        confidence=signal.confidence,
        previous_value=signal.previous_value,
        current_value=signal.current_value,
        detected_at=signal.detected_at,
        status=signal.status,
        metrics=json.loads(signal.metrics_json or "{}"),
        diagnostics=json.loads(signal.diagnostics_json or "{}"),
        sample_urls=json.loads(signal.sample_urls_json or "[]"),
        proposed_action=signal.proposed_action,
        resolution_notes=signal.resolution_notes,
        acknowledged_at=signal.acknowledged_at,
        resolved_at=signal.resolved_at,
    )


@router.post("/detect", response_model=dict)
async def detect_mapping_drift(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    service = DriftDetectionService(db)
    return await service.detect_for_source(source_id)


@router.get("", response_model=MappingDriftSignalListResponse)
async def list_drift_signals(
    source_id: str,
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    mapping_id = source.published_mapping_version_id or source.active_mapping_version_id
    items = await crud.list_mapping_drift_signals(db, source_id=source_id, status=status, severity=severity, skip=skip, limit=limit)
    health = await crud.get_mapping_health_state(db, source_id=source_id, mapping_version_id=mapping_id)
    open_items = [item for item in items if item.status in {"open", "acknowledged"}]
    return MappingDriftSignalListResponse(
        source_id=source_id,
        active_mapping_version_id=mapping_id,
        mapping_health=health,
        open_high_severity=sum(1 for item in open_items if item.severity == "high"),
        items=[_serialize_signal(item) for item in items],
        total=len(items),
    )


@router.get("/{signal_id}", response_model=MappingDriftSignalResponse)
async def get_drift_signal(
    source_id: str,
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    signal = await crud.get_mapping_drift_signal(db, source_id=source_id, signal_id=signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Drift signal not found")
    return _serialize_signal(signal)


@router.post("/{signal_id}/acknowledge", response_model=MappingDriftSignalResponse)
async def acknowledge_drift_signal(
    source_id: str,
    signal_id: str,
    body: DriftSignalStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    try:
        signal = await crud.update_mapping_drift_signal_status(
            db,
            source_id=source_id,
            signal_id=signal_id,
            status="acknowledged",
            resolution_notes=body.resolution_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_signal(signal)


@router.post("/{signal_id}/dismiss", response_model=MappingDriftSignalResponse)
async def dismiss_drift_signal(
    source_id: str,
    signal_id: str,
    body: DriftSignalStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    try:
        signal = await crud.update_mapping_drift_signal_status(
            db,
            source_id=source_id,
            signal_id=signal_id,
            status="dismissed",
            resolution_notes=body.resolution_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_signal(signal)


@router.post("/{signal_id}/resolve", response_model=MappingDriftSignalResponse)
async def resolve_drift_signal(
    source_id: str,
    signal_id: str,
    body: DriftSignalStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    try:
        signal = await crud.update_mapping_drift_signal_status(
            db,
            source_id=source_id,
            signal_id=signal_id,
            status="resolved",
            resolution_notes=body.resolution_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize_signal(signal)


@router.post("/{signal_id}/remap-draft", response_model=DriftRemapDraftResponse)
async def create_remap_draft_from_signal(
    source_id: str,
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    signal = await crud.get_mapping_drift_signal(db, source_id=source_id, signal_id=signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Drift signal not found")
    try:
        draft = await crud.create_drift_remap_draft(
            db,
            source_id=source_id,
            generated_from_signal_id=signal_id,
            created_by="admin",
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return DriftRemapDraftResponse(
        source_id=source_id,
        signal_id=signal_id,
        draft_mapping_version_id=draft.id,
        based_on_mapping_version_id=signal.mapping_version_id,
        status="draft_created",
    )


@router.post("/{signal_id}/ignore", response_model=MappingDriftSignalResponse)
async def ignore_drift_signal(
    source_id: str,
    signal_id: str,
    body: DriftSignalStatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    signal = await crud.update_mapping_drift_signal_status(
        db,
        source_id=source_id,
        signal_id=signal_id,
        status="dismissed",
        resolution_notes=body.resolution_notes or "Ignored as false positive",
    )
    return _serialize_signal(signal)


@router.post("/{signal_id}/rerun-extraction")
async def rerun_extraction_for_signal(
    source_id: str,
    signal_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    signal = await crud.get_mapping_drift_signal(db, source_id=source_id, signal_id=signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="Drift signal not found")
    if not signal.page_id:
        raise HTTPException(status_code=400, detail="Signal has no page context")
    result = await PipelineRunner(db, ai_client=None).run_reextract_page(signal.page_id)
    return {"source_id": source_id, "signal_id": signal_id, "status": "reprocessed", "result": result}


@overview_router.get("/drift-signals", response_model=MappingDriftSignalListResponse)
async def list_all_drift_signals(
    source_id: str | None = Query(default=None),
    status: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    if source_id is None:
        raise HTTPException(status_code=400, detail="source_id is required")
    items = await crud.list_mapping_drift_signals(db, source_id=source_id, status=status, severity=severity, skip=skip, limit=limit)
    source = await crud.get_source(db, source_id)
    mapping_id = source.published_mapping_version_id if source else None
    health = await crud.get_mapping_health_state(db, source_id=source_id, mapping_version_id=mapping_id)
    return MappingDriftSignalListResponse(
        source_id=source_id,
        active_mapping_version_id=mapping_id,
        mapping_health=health,
        open_high_severity=sum(1 for item in items if item.status in {"open", "acknowledged"} and item.severity == "high"),
        items=[_serialize_signal(item) for item in items],
        total=len(items),
    )


@overview_router.get("/drift-summary/{source_id}", response_model=DriftSummaryResponse)
async def get_drift_summary(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    summary = await ExtractionDriftDetectionService(db).analyze_source(source_id)
    return DriftSummaryResponse(**summary)


@overview_router.get("/drift-fields/{source_id}", response_model=DriftFieldsResponse)
async def get_drift_fields(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    signals = await crud.list_mapping_drift_signals(db, source_id=source_id, status=None, severity=None, skip=0, limit=1000)
    counts: dict[str, int] = {}
    for signal in signals:
        if signal.field_name:
            counts[signal.field_name] = counts.get(signal.field_name, 0) + 1
    return DriftFieldsResponse(source_id=source_id, fields=[{"field_name": key, "count": value} for key, value in sorted(counts.items(), key=lambda x: x[1], reverse=True)])
