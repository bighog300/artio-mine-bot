import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.client import OpenAIClient
from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import ConflictResolveRequest
from app.db import crud
from app.extraction.artist_merge import derive_artist_family_key
from app.pipeline.runner import PipelineRunner

router = APIRouter(prefix="/review", tags=["review"])



def _parse_raw(raw_data: str | None) -> dict[str, Any]:
    if not raw_data:
        return {}
    try:
        loaded = json.loads(raw_data)
        if isinstance(loaded, dict):
            return loaded
    except json.JSONDecodeError:
        return {}
    return {}


async def _get_artist_or_404(db: AsyncSession, artist_id: str):
    record = await crud.get_record(db, artist_id)
    if record is None or record.record_type != "artist":
        raise HTTPException(status_code=404, detail="Artist record not found")
    return record


@router.get("/artists/{artist_id}")
async def get_review_artist(
    artist_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    artist = await _get_artist_or_404(db, artist_id)
    payload = _parse_raw(artist.raw_data)
    family_key = payload.get("artist_family_key") or derive_artist_family_key(artist.source_url or "")

    related = payload.get("related") or {}
    if family_key:
        pages = await crud.list_pages_for_artist_family(
            db,
            source_id=artist.source_id,
            family_key=family_key,
        )
        family_records = await crud.list_records_for_artist_family(
            db,
            source_id=artist.source_id,
            page_ids=[page.id for page in pages],
        )
        for record in family_records:
            key = {
                "exhibition": "exhibitions",
                "artist_article": "articles",
                "artist_press": "press",
                "artist_memory": "memories",
            }.get(record.record_type)
            if key is None:
                continue
            related.setdefault(key, []).append(
                {
                    "id": record.id,
                    "title": record.title,
                    "source_url": record.source_url,
                    "status": record.status,
                }
            )

    return {
        "id": artist.id,
        "source_id": artist.source_id,
        "title": artist.title,
        "canonical_fields": payload.get("artist_payload", {}),
        "completeness_score": payload.get("completeness_score", 0),
        "missing_fields": payload.get("missing_fields", []),
        "provenance": payload.get("provenance") or payload.get("artist_payload_provenance", {}),
        "conflicts": payload.get("conflicts", {}),
        "related": related,
    }


@router.get("/artists")
async def list_review_artists(
    completeness_lt: int | None = None,
    has_conflicts: bool | None = None,
    missing_field: str | None = None,
    source_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    artists = await crud.list_artist_records(db, source_id=source_id)
    items = []
    for artist in artists:
        payload = _parse_raw(artist.raw_data)
        conflicts = payload.get("conflicts", {})
        missing_fields = payload.get("missing_fields", [])
        score = payload.get("completeness_score", 0)

        if completeness_lt is not None and score >= completeness_lt:
            continue
        if has_conflicts is True and not conflicts:
            continue
        if has_conflicts is False and conflicts:
            continue
        if missing_field and missing_field not in missing_fields:
            continue

        items.append(
            {
                "id": artist.id,
                "source_id": artist.source_id,
                "title": artist.title,
                "completeness_score": score,
                "missing_fields": missing_fields,
                "has_conflicts": bool(conflicts),
                "conflict_fields": sorted(list(conflicts.keys())),
            }
        )

    return {"items": items, "total": len(items)}


@router.post("/artists/{artist_id}/resolve")
async def resolve_artist_conflict(
    artist_id: str,
    body: ConflictResolveRequest,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("merge")),
):
    artist = await _get_artist_or_404(db, artist_id)
    payload = _parse_raw(artist.raw_data)
    conflicts = payload.setdefault("conflicts", {})
    if body.field not in conflicts:
        raise HTTPException(status_code=400, detail=f"No conflict for field '{body.field}'")

    payload.setdefault("artist_payload", {})[body.field] = body.selected_value
    payload.setdefault("provenance", {}).setdefault(body.field, {}).update(
        {"value": body.selected_value}
    )
    payload.setdefault("resolved_conflicts", {})[body.field] = {
        "selected_value": body.selected_value,
    }

    for entry in conflicts[body.field]:
        entry["selected"] = entry.get("value") == body.selected_value
        entry["resolved"] = True

    await crud.update_record(db, artist.id, raw_data=json.dumps(payload))
    await crud.create_audit_action(
        db,
        action_type="conflict_resolution",
        record_id=artist.id,
        source_id=artist.source_id,
        affected_record_ids=[artist.id],
        details={"field": body.field, "selected_value": body.selected_value},
    )
    return {
        "id": artist.id,
        "field": body.field,
        "selected_value": body.selected_value,
        "status": "resolved",
    }


@router.post("/artists/{artist_id}/rerun")
async def rerun_artist(
    artist_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("rerun")),
):
    artist = await _get_artist_or_404(db, artist_id)
    payload = _parse_raw(artist.raw_data)
    family_key = payload.get("artist_family_key") or derive_artist_family_key(artist.source_url or "")
    if family_key is None:
        raise HTTPException(status_code=400, detail="Artist family key unavailable")

    runner = PipelineRunner(db=db, ai_client=OpenAIClient())
    result = await runner.rerun_artist_family(source_id=artist.source_id, family_key=family_key)
    await crud.create_audit_action(
        db,
        action_type="rerun",
        record_id=artist.id,
        source_id=artist.source_id,
        affected_record_ids=[artist.id],
        details={"family_key": family_key},
    )
    return {
        "artist_id": artist.id,
        "family_key": family_key,
        "result": result,
    }
