from fastapi import APIRouter, Depends, HTTPException
import json
import structlog
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rbac import require_permission
from app.api.schemas import (
    SourceCreate,
    SourceDetailResponse,
    SourceResponse,
    SourceStats,
    SourceUpdate,
)
from app.db import crud

router = APIRouter(prefix="/sources", tags=["sources"])
logger = structlog.get_logger()


@router.get("", response_model=dict)
async def list_sources(
    skip: int = 0,
    limit: int = 50,
    enabled: bool | None = None,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    sources = await crud.list_sources(db, skip=skip, limit=limit, enabled=enabled)
    total = len(sources)  # Simple count for now

    items = []
    for source in sources:
        stats_data = await crud.get_source_stats(db, source.id)
        source_dict = SourceResponse.model_validate(source).model_dump()
        source_dict["stats"] = SourceStats(**stats_data).model_dump()
        items.append(source_dict)

    return {"items": items, "total": total, "skip": skip, "limit": limit}


@router.post("", response_model=SourceResponse, status_code=201)
async def create_source(
    body: SourceCreate,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    existing = await crud.get_source_by_url(db, body.url)
    if existing:
        raise HTTPException(status_code=409, detail="Source with this URL already exists")

    try:
        source = await crud.create_source(
            db,
            url=body.url,
            name=body.name,
            crawl_hints=json.dumps(body.crawl_hints) if body.crawl_hints is not None else None,
            extraction_rules=json.dumps(body.extraction_rules) if body.extraction_rules is not None else None,
            max_depth=body.max_depth,
            enabled=body.enabled,
        )
        return source
    except IntegrityError as exc:
        await db.rollback()
        logger.warning(
            "source_create_integrity_error",
            url=body.url,
            error=str(exc),
        )
        raise HTTPException(status_code=409, detail="Source with this URL already exists") from exc
    except SQLAlchemyError as exc:
        await db.rollback()
        logger.error(
            "source_create_db_error",
            url=body.url,
            error=str(exc),
        )
        raise HTTPException(
            status_code=500,
            detail="Database error while creating source. Check API logs for details.",
        ) from exc


@router.get("/{source_id}", response_model=SourceDetailResponse)
async def get_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    return source


@router.patch("/{source_id}", response_model=SourceResponse)
async def update_source(
    source_id: str,
    body: SourceUpdate,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    kwargs = {k: v for k, v in body.model_dump().items() if v is not None}
    if "crawl_hints" in kwargs:
        kwargs["crawl_hints"] = json.dumps(kwargs["crawl_hints"])
    if "extraction_rules" in kwargs:
        kwargs["extraction_rules"] = json.dumps(kwargs["extraction_rules"])
    if kwargs:
        source = await crud.update_source(db, source_id, **kwargs)
    return source


@router.delete("/{source_id}", status_code=204)
async def delete_source(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("write")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    await crud.delete_source(db, source_id)


@router.get("/{source_id}/jobs")
async def list_source_jobs(
    source_id: str,
    db: AsyncSession = Depends(get_db),
    _role: str = Depends(require_permission("read")),
):
    source = await crud.get_source(db, source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    jobs = await crud.list_jobs(db, source_id=source_id)
    return {
        "items": [
            {
                "id": job.id,
                "source_id": job.source_id,
                "job_type": job.job_type,
                "status": job.status,
                "attempts": job.attempts,
                "started_at": job.started_at,
                "completed_at": job.completed_at,
                "error_message": job.error_message,
            }
            for job in jobs
        ]
    }
