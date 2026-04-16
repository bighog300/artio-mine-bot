import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db import crud
from app.services.audit import AuditService

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def list_audit_actions(
    action_type: str | None = None,
    source_id: str | None = None,
    record_id: str | None = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    actions = await crud.list_audit_actions(
        db,
        action_type=action_type,
        source_id=source_id,
        record_id=record_id,
        skip=skip,
        limit=limit,
    )
    items = []
    for action in actions:
        try:
            affected_record_ids = json.loads(action.affected_record_ids)
        except json.JSONDecodeError:
            affected_record_ids = []
        try:
            details = json.loads(action.details_json) if action.details_json else {}
        except json.JSONDecodeError:
            details = {}

        items.append(
            {
                "id": action.id,
                "action_type": action.action_type,
                "user": action.user_id,
                "source_id": action.source_id,
                "record_id": action.record_id,
                "affected_records": affected_record_ids,
                "details": details,
                "timestamp": action.created_at,
            }
        )

    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.get("/events")
async def get_audit_trail(
    event_type: str | None = None,
    entity_type: str | None = None,
    user_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    return await AuditService.list_events(
        db,
        event_type=event_type,
        entity_type=entity_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
        skip=skip,
        limit=limit,
    )


@router.get("/events/export", response_class=PlainTextResponse)
async def export_audit_trail(
    event_type: str | None = None,
    entity_type: str | None = None,
    user_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    search: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await AuditService.export_events_csv(
        db,
        event_type=event_type,
        entity_type=entity_type,
        user_id=user_id,
        date_from=date_from,
        date_to=date_to,
        search=search,
    )


@router.get("/events/{event_id}")
async def get_audit_event(
    event_id: str,
    db: AsyncSession = Depends(get_db),
):
    event = await AuditService.get_event(db, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return event
