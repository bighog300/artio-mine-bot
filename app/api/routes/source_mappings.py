import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import MappingFamilyRuleResponse, MappingSuggestionDraftRequest, MappingSuggestionResponse
from app.db import crud
from app.source_mapper.mapping_suggestion_service import MappingSuggestionService

router = APIRouter(prefix="/sources/{source_id}/mappings", tags=["source-mappings"])


def _serialize_mapping(version) -> MappingSuggestionResponse:
    mapping_json = json.loads(version.mapping_json or "{}")
    summary = json.loads(version.summary_json or "{}") if version.summary_json else {}
    family_rules = [MappingFamilyRuleResponse(**rule) for rule in mapping_json.get("family_rules", [])]
    return MappingSuggestionResponse(
        id=version.id,
        source_id=version.source_id,
        based_on_profile_id=version.based_on_profile_id,
        version_number=version.version_number,
        status=version.status,
        created_at=version.created_at,
        family_rules=family_rules,
        diagnostics=summary,
    )


@router.post("/draft", response_model=MappingSuggestionResponse, status_code=201)
async def create_mapping_draft_from_profile(
    source_id: str,
    body: MappingSuggestionDraftRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    profile = await crud.get_source_profile(db, source_id, body.profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")

    service = MappingSuggestionService(db)
    version = await service.generate_draft(source_id, body.profile_id)
    return _serialize_mapping(version)


@router.get("/{mapping_id}", response_model=MappingSuggestionResponse)
async def get_mapping_draft(
    source_id: str,
    mapping_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    version = await crud.get_mapping_suggestion_draft(db, source_id=source_id, mapping_id=mapping_id)
    if version is None:
        raise HTTPException(status_code=404, detail="Mapping version not found")
    return _serialize_mapping(version)
