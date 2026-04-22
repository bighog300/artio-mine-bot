from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import EntityRelationshipResponse, EntityResponse, PaginatedResponse
from app.db import crud

router = APIRouter(tags=["entities"])


@router.get("/entities", response_model=PaginatedResponse)
async def list_entities(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=500),
    entity_type: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
):
    items = await crud.list_entities(db, entity_type=entity_type, skip=skip, limit=limit)
    total = await crud.count_entities(db, entity_type=entity_type)
    return PaginatedResponse(items=[EntityResponse.model_validate(item) for item in items], total=total, skip=skip, limit=limit)


@router.get("/entities/{entity_id}", response_model=EntityResponse)
async def get_entity(entity_id: str, db: AsyncSession = Depends(get_db)):
    entity = await crud.get_entity(db, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    return EntityResponse.model_validate(entity)


@router.get("/entities/{entity_id}/records")
async def get_entity_records(entity_id: str, db: AsyncSession = Depends(get_db)):
    entity = await crud.get_entity(db, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    records = await crud.list_records_for_entity(db, entity_id)
    return [
        {
            "id": record.id,
            "source_id": record.source_id,
            "record_type": record.record_type,
            "title": record.title,
            "confidence_score": record.confidence_score,
            "source_url": record.source_url,
            "updated_at": record.updated_at,
        }
        for record in records
    ]


@router.get("/entities/{entity_id}/relationships", response_model=list[EntityRelationshipResponse])
async def get_entity_relationships(entity_id: str, db: AsyncSession = Depends(get_db)):
    entity = await crud.get_entity(db, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")
    relationships = await crud.list_relationships_for_entity(db, entity_id)
    return [EntityRelationshipResponse.model_validate(rel) for rel in relationships]


@router.get("/entity-conflicts")
async def list_entity_conflicts(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    return {"items": await crud.list_entity_conflicts(db, limit=limit), "limit": limit}
