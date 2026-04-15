from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import APIPrincipal, require_api_key
from app.api.cache import response_cache
from app.api.deps import get_db
from app.db import crud

router = APIRouter(prefix="/v1", tags=["public-v1"])


@router.get("/search")
async def v1_search(
    q: str | None = None,
    record_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    principal: APIPrincipal = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    cache_key = f"v1:search:{principal.tenant_id}:{q}:{record_type}:{skip}:{limit}"
    cached = await response_cache.get(cache_key)
    if cached is not None:
        return cached

    records = await crud.list_records(
        db,
        tenant_id=principal.tenant_id,
        record_type=record_type,
        search=q,
        skip=skip,
        limit=limit,
    )
    total = await crud.count_records(
        db,
        tenant_id=principal.tenant_id,
        record_type=record_type,
        search=q,
    )
    payload = {
        "version": "v1",
        "items": [
            {
                "id": row.id,
                "type": row.record_type,
                "title": row.title,
                "description": row.description,
                "source_url": row.source_url,
                "created_at": row.created_at,
            }
            for row in records
        ],
        "total": total,
        "skip": skip,
        "limit": limit,
    }
    await response_cache.set(cache_key, payload, ttl_seconds=60)
    return payload


@router.get("/graph")
async def v1_graph(
    record_id: str,
    principal: APIPrincipal = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    cache_key = f"v1:graph:{principal.tenant_id}:{record_id}"
    cached = await response_cache.get(cache_key)
    if cached is not None:
        return cached

    relationships = await crud.list_relationships_for_record(
        db,
        source_id=None,
        record_id=record_id,
        tenant_id=principal.tenant_id,
    )
    payload = {
        "version": "v1",
        "record_id": record_id,
        "edges": [
            {
                "from_record_id": edge.from_record_id,
                "to_record_id": edge.to_record_id,
                "relationship_type": edge.relationship_type,
            }
            for edge in relationships
        ],
    }
    await response_cache.set(cache_key, payload, ttl_seconds=120)
    return payload


@router.get("/export")
async def v1_export(
    record_type: str | None = None,
    skip: int = 0,
    limit: int = 100,
    principal: APIPrincipal = Depends(require_api_key),
    db: AsyncSession = Depends(get_db),
):
    limit = max(1, min(limit, 100))
    cache_key = f"v1:export:{principal.tenant_id}:{record_type}:{skip}:{limit}"
    cached = await response_cache.get(cache_key)
    if cached is not None:
        return cached

    rows = await crud.list_records(
        db,
        tenant_id=principal.tenant_id,
        record_type=record_type,
        skip=skip,
        limit=limit,
    )
    payload = {
        "version": "v1",
        "items": [
            {
                "id": row.id,
                "type": row.record_type,
                "title": row.title,
                "description": row.description,
                "venue_name": row.venue_name,
                "start_date": row.start_date,
                "end_date": row.end_date,
            }
            for row in rows
        ],
        "count": len(rows),
    }
    await response_cache.set(cache_key, payload, ttl_seconds=120)
    return payload
