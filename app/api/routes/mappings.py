from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.db import crud
from app.db.models import Source, SourceMappingVersion

router = APIRouter(prefix="/mappings", tags=["mappings"])


def _mapping_status(mapping: SourceMappingVersion) -> str:
    return "healthy" if mapping.status in {"approved", "published", "active"} else "degraded"


def _serialize_mapping_list_item(mapping: SourceMappingVersion, source: Source) -> dict[str, object]:
    return {
        "id": mapping.id,
        "name": source.name or source.url,
        "version": int(mapping.version_number or 1),
        "status": _mapping_status(mapping),
        "updated_at": mapping.updated_at,
        "drift_impact": 0.0,
    }


def _serialize_mapping_detail(mapping: SourceMappingVersion, source: Source) -> dict[str, object]:
    return {
        **_serialize_mapping_list_item(mapping, source),
        "source_id": source.id,
        "fields": [],
    }


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
        items.append(_serialize_mapping_list_item(mapping, source))

    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.get("/{mapping_id}")
async def get_mapping_detail(
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    mapping = await crud.get_mapping_suggestion_version(db, mapping_id=mapping_id)
    if mapping is None:
        raise HTTPException(status_code=404, detail="Mapping not found")
    source = await crud.get_source(db, mapping.source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    return _serialize_mapping_detail(mapping, source)
