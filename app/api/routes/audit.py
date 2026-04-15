import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db import crud

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
