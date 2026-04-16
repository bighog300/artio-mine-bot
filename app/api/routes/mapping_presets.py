from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import SourceMappingPresetCreateRequest, SourceMappingPresetSummary
from app.db import crud

router = APIRouter(prefix="/sources/{source_id}/mapping-presets", tags=["source-mapper"])


@router.get("", response_model=dict)
async def list_mapping_presets(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    items = await crud.list_source_mapping_presets(db, source_id=source_id, tenant_id=source.tenant_id)
    return {
        "items": [SourceMappingPresetSummary.model_validate(item).model_dump() for item in items],
        "total": len(items),
    }


@router.post("", response_model=SourceMappingPresetSummary, status_code=201)
async def create_mapping_preset(
    source_id: str,
    body: SourceMappingPresetCreateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="Preset name is required")
    if not body.draft_id and not body.mapping_version_id:
        raise HTTPException(status_code=400, detail="draft_id or mapping_version_id is required")

    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    try:
        preset = await crud.create_source_mapping_preset_from_version(
            db,
            source_id=source_id,
            tenant_id=source.tenant_id,
            name=body.name.strip(),
            description=body.description,
            draft_id=body.draft_id,
            mapping_version_id=body.mapping_version_id,
            include_statuses=body.include_statuses,
            created_by="admin",
        )
    except ValueError as exc:
        message = str(exc)
        if "not found" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Preset name already exists for this source") from exc

    return SourceMappingPresetSummary.model_validate(preset)


@router.delete("/{preset_id}", response_model=dict)
async def delete_mapping_preset(
    source_id: str,
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    deleted = await crud.delete_source_mapping_preset(db, preset_id, source_id=source_id, tenant_id=source.tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Mapping preset not found")
    return {"ok": True}


@router.post("/{preset_id}/apply", response_model=dict)
async def apply_mapping_preset(
    source_id: str,
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    try:
        updated = await crud.apply_source_mapping_preset_to_source(
            db,
            source_id=source_id,
            preset_id=preset_id,
            tenant_id=source.tenant_id,
        )
    except ValueError as exc:
        message = str(exc)
        if "not found" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc

    runtime_map, runtime_map_source = await crud.get_active_runtime_map(db, source_id)
    return {
        "source_id": updated.id,
        "active_mapping_preset_id": updated.active_mapping_preset_id,
        "runtime_mapping_updated_at": updated.runtime_mapping_updated_at,
        "runtime_map_source": runtime_map_source,
        "has_runtime_map": runtime_map is not None,
    }


@router.get("/runtime-map", response_model=dict)
async def get_source_runtime_map(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    runtime_map, runtime_map_source = await crud.get_active_runtime_map(db, source_id)
    return {
        "source_id": source_id,
        "runtime_map_source": runtime_map_source,
        "active_mapping_preset_id": source.active_mapping_preset_id,
        "runtime_mapping_updated_at": source.runtime_mapping_updated_at,
        "runtime_map": runtime_map,
    }
