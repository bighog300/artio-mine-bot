from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.db.models import Source, SourceMappingVersion

router = APIRouter(prefix="/mappings", tags=["mappings"])


@router.get("")
async def list_mappings(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    stmt = (
        select(SourceMappingVersion, Source)
        .join(Source, SourceMappingVersion.source_id == Source.id)
        .order_by(SourceMappingVersion.updated_at.desc())
        .offset(skip)
        .limit(limit)
    )
    try:
        rows = (await db.execute(stmt)).all()
    except SQLAlchemyError:
        return {"items": [], "total": 0, "skip": skip, "limit": limit}
    items = []
    for mapping, source in rows:
        status = "healthy" if mapping.status in {"approved", "published", "active"} else "degraded"
        items.append(
            {
                "id": mapping.id,
                "name": source.name or source.url,
                "version": int(mapping.version_number or 1),
                "status": status,
                "updated_at": mapping.updated_at,
                "drift_impact": 0.0,
            }
        )

    return {"items": items, "total": len(items), "skip": skip, "limit": limit}
