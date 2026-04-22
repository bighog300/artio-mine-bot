import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import MappingRepairProposalListResponse, MappingRepairProposalResponse
from app.db import crud
from app.source_mapper.auto_repair import AutoRepairService

router = APIRouter(tags=["mapping-repair"])


def _serialize(item) -> MappingRepairProposalResponse:
    return MappingRepairProposalResponse(
        id=item.id,
        source_id=item.source_id,
        mapping_version_id=item.mapping_version_id,
        field_name=item.field_name,
        old_selector=item.old_selector,
        proposed_selector=item.proposed_selector,
        confidence_score=item.confidence_score,
        supporting_pages=json.loads(item.supporting_pages_json or "[]"),
        drift_signals_used=json.loads(item.drift_signals_used_json or "[]"),
        validation_results=json.loads(item.validation_results_json or "{}"),
        occurrence_count=int(item.occurrence_count or 1),
        priority_score=float(item.priority_score or 0.0),
        strategy_used=item.strategy_used,
        reasoning=item.reasoning,
        evidence=json.loads(item.evidence_json or "{}"),
        status=item.status,
        reviewed_by=item.reviewed_by,
        reviewed_at=item.reviewed_at,
        applied_mapping_version_id=item.applied_mapping_version_id,
        feedback=json.loads(item.feedback_json or "{}"),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.get("/mapping-repair-proposals", response_model=MappingRepairProposalListResponse)
async def list_mapping_repair_proposals(
    source_id: str = Query(...),
    status: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    items = await crud.list_mapping_repair_proposals(db, source_id=source_id, status=status, skip=skip, limit=limit)
    return MappingRepairProposalListResponse(source_id=source_id, items=[_serialize(item) for item in items], total=len(items))


@router.post("/mapping-repair/{proposal_id}/approve", response_model=MappingRepairProposalResponse)
async def approve_mapping_repair_proposal(
    proposal_id: str,
    source_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    try:
        proposal = await crud.update_mapping_repair_proposal(
            db,
            source_id=source_id,
            proposal_id=proposal_id,
            status="VALIDATED",
            reviewed_by="admin",
            feedback={"decision": "approved"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(proposal)


@router.post("/mapping-repair/{proposal_id}/reject", response_model=MappingRepairProposalResponse)
async def reject_mapping_repair_proposal(
    proposal_id: str,
    source_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    try:
        proposal = await crud.update_mapping_repair_proposal(
            db,
            source_id=source_id,
            proposal_id=proposal_id,
            status="REJECTED",
            reviewed_by="admin",
            feedback={"decision": "rejected"},
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return _serialize(proposal)


@router.post("/mapping-repair/{proposal_id}/apply", response_model=MappingRepairProposalResponse)
async def apply_mapping_repair_proposal(
    proposal_id: str,
    source_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rollback")),
):
    service = AutoRepairService(db)
    try:
        applied_mapping_id = await service.apply_proposal(source_id, proposal_id, reviewed_by="admin")
        proposal = await crud.update_mapping_repair_proposal(
            db,
            source_id=source_id,
            proposal_id=proposal_id,
            status="APPLIED",
            reviewed_by="admin",
            applied_mapping_version_id=applied_mapping_id,
            feedback={"decision": "applied"},
        )
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize(proposal)
