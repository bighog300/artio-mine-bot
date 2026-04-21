import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import SourceProfileResponse, SourceProfileRunRequest, UrlFamilyResponse
from app.db import crud
from app.source_profiler.service import SourceProfilerService

router = APIRouter(prefix="/sources/{source_id}/profiles", tags=["source-profiler"])


def _parse_json(raw: str | None, default):
    try:
        return json.loads(raw or json.dumps(default))
    except (TypeError, json.JSONDecodeError):
        return default


def _serialize_family(row) -> UrlFamilyResponse:
    return UrlFamilyResponse(
        id=row.id,
        family_key=row.family_key,
        family_label=row.family_label,
        path_pattern=row.path_pattern,
        page_type_candidate=row.page_type_candidate,
        confidence=float(row.confidence),
        sample_urls=_parse_json(row.sample_urls_json, []),
        follow_policy_candidate=row.follow_policy_candidate,
        pagination_policy_candidate=row.pagination_policy_candidate,
        include_by_default=bool(row.include_by_default),
        diagnostics=_parse_json(row.diagnostics_json, {}),
    )


async def _serialize_profile(db: AsyncSession, profile) -> SourceProfileResponse:
    families = await crud.list_url_families(db, profile.id)
    return SourceProfileResponse(
        id=profile.id,
        source_id=profile.source_id,
        seed_url=profile.seed_url,
        status=profile.status,
        started_at=profile.started_at,
        completed_at=profile.completed_at,
        site_fingerprint=_parse_json(profile.site_fingerprint, {}),
        sitemap_urls=_parse_json(profile.sitemap_urls, []),
        nav_discovery_summary=_parse_json(profile.nav_discovery_summary, {}),
        profile_metrics=_parse_json(profile.profile_metrics_json, {}),
        families=[_serialize_family(item) for item in families],
    )


@router.post("", response_model=SourceProfileResponse, status_code=201)
async def run_source_profile(
    source_id: str,
    body: SourceProfileRunRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")
    service = SourceProfilerService(db)
    profile, _ = await service.profile_source(source, max_pages=body.max_pages)
    return await _serialize_profile(db, profile)


@router.get("/{profile_id}", response_model=SourceProfileResponse)
async def get_source_profile(
    source_id: str,
    profile_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    profile = await crud.get_source_profile(db, source_id, profile_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Profile not found")
    return await _serialize_profile(db, profile)
