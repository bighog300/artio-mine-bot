import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import (
    MappingTemplateCreateRequest,
    MappingTemplateImportRequest,
    MappingTemplateSummary,
    SourceMappingPresetCreateRequest,
    SourceMappingPresetSummary,
)
from app.db import crud

router = APIRouter(prefix="/sources/{source_id}/mapping-presets", tags=["source-mapper"])
template_router = APIRouter(prefix="/mapping-templates", tags=["source-mapper"])
preset_export_router = APIRouter(prefix="/mapping-presets", tags=["source-mapper"])


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

    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    resolved_mapping_version_id = body.mapping_version_id
    if not body.draft_id and not resolved_mapping_version_id:
        resolved_mapping_version_id = source.active_mapping_version_id
        if not resolved_mapping_version_id:
            raise HTTPException(
                status_code=422,
                detail="Source has no published mapping version — provide draft_id",
            )

    try:
        preset = await crud.create_source_mapping_preset_from_version(
            db,
            source_id=source_id,
            tenant_id=source.tenant_id,
            name=body.name.strip(),
            description=body.description,
            draft_id=body.draft_id,
            mapping_version_id=resolved_mapping_version_id,
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


@preset_export_router.get("/{preset_id}/export", response_model=dict)
async def export_mapping_preset(
    preset_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    try:
        payload = await crud.export_source_mapping_preset(db, preset_id=preset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return payload


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


@template_router.get("", response_model=dict)
async def list_templates(
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    items = await crud.list_mapping_templates(db)
    return {"items": [MappingTemplateSummary.model_validate(item).model_dump() for item in items], "total": len(items)}


@template_router.post("", response_model=MappingTemplateSummary, status_code=201)
async def create_template(
    body: MappingTemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    validation = crud.validate_mapping_template(body.template_json)
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail={"message": "Invalid mapping template", "errors": validation["errors"]})
    try:
        template = await crud.create_mapping_template(
            db,
            name=body.name.strip(),
            description=body.description,
            template_json=body.template_json,
            schema_version=body.schema_version,
            created_by="admin",
            is_system=False,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Template name already exists") from exc
    return MappingTemplateSummary.model_validate(template)


@template_router.post("/import", response_model=MappingTemplateSummary, status_code=201)
async def import_template_from_text(
    body: MappingTemplateImportRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    try:
        parsed = json.loads(body.content)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="Template content is not valid JSON") from exc

    template_json = parsed.get("payload") if isinstance(parsed, dict) and "payload" in parsed else parsed
    if not isinstance(template_json, dict):
        raise HTTPException(status_code=422, detail="Template payload must be a JSON object")

    schema_version = int(parsed.get("schema_version", 1)) if isinstance(parsed, dict) else 1
    validation = crud.validate_mapping_template(template_json)
    if not validation["ok"]:
        raise HTTPException(status_code=422, detail={"message": "Invalid mapping template", "errors": validation["errors"]})
    try:
        template = await crud.create_mapping_template(
            db,
            name=body.name.strip(),
            description=body.description,
            template_json=template_json,
            schema_version=schema_version,
            created_by="admin",
            is_system=False,
        )
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Template name already exists") from exc
    return MappingTemplateSummary.model_validate(template)


@template_router.post("/{template_id}/apply", response_model=dict)
async def apply_template_to_source(
    template_id: str,
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    try:
        source = await crud.apply_mapping_template_to_source(db, source_id=source_id, template_id=template_id)
    except ValueError as exc:
        message = str(exc)
        status = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status, detail=message) from exc
    runtime_map, runtime_map_source = await crud.get_active_runtime_map(db, source_id)
    return {
        "source_id": source.id,
        "runtime_map_source": runtime_map_source,
        "runtime_mapping_updated_at": source.runtime_mapping_updated_at,
        "has_runtime_map": runtime_map is not None,
    }
