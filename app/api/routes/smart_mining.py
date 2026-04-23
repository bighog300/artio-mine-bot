from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.smart_miner import SmartMiner
from app.ai.templates import TemplateLibrary
from app.api.deps import get_db
from app.db import crud
from app.db.database import AsyncSessionLocal

router = APIRouter(prefix="/smart-mine", tags=["smart-mining"])
logger = structlog.get_logger()

_miner: SmartMiner | None = None
_template_library = TemplateLibrary()
_job_statuses: dict[str, dict] = {}


def _get_miner() -> SmartMiner:
    global _miner
    if _miner is None:
        _miner = SmartMiner()
    return _miner


class SmartMineCreateRequest(BaseModel):
    url: str
    name: str | None = None
    source_id: str | None = None


class SmartMineCreateResponse(BaseModel):
    source_id: str
    status: str
    message: str


class SmartMineStatusResponse(BaseModel):
    source_id: str
    status: str
    pages_count: int
    records_count: int
    updated_at: datetime
    job_status: Literal["queued", "running", "completed", "failed"]
    error: str | None = None


class SmartTemplateListItem(BaseModel):
    id: str
    name: str
    usage_count: int = 0


async def _execute_smart_mine(source_id: str, url: str) -> None:
    _job_statuses[source_id] = {
        "job_status": "running",
        "updated_at": datetime.now(UTC),
        "error": None,
    }
    try:
        async with AsyncSessionLocal() as session:
            await _get_miner().smart_mine(session, source_id, url)
        _job_statuses[source_id] = {
            "job_status": "completed",
            "updated_at": datetime.now(UTC),
            "error": None,
        }
    except (ValueError, RuntimeError, OSError) as exc:
        logger.exception("smart_mine_background_failed", source_id=source_id, error=str(exc))
        _job_statuses[source_id] = {
            "job_status": "failed",
            "updated_at": datetime.now(UTC),
            "error": str(exc),
        }


@router.post("/", response_model=SmartMineCreateResponse, status_code=200)
async def create_smart_mine(
    request: SmartMineCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> SmartMineCreateResponse:
    if request.source_id:
        source = await crud.get_source(db, request.source_id)
        if source is None:
            raise HTTPException(status_code=404, detail="Source not found")
    else:
        source = await crud.create_source(db, url=request.url, name=request.name or request.url)

    _job_statuses[source.id] = {
        "job_status": "queued",
        "updated_at": datetime.now(UTC),
        "error": None,
    }
    background_tasks.add_task(_execute_smart_mine, source.id, request.url)

    return SmartMineCreateResponse(
        source_id=source.id,
        status="queued",
        message="Smart mining job accepted",
    )


@router.get("/{source_id}/status", response_model=SmartMineStatusResponse, status_code=200)
async def get_smart_mine_status(source_id: str, db: AsyncSession = Depends(get_db)) -> SmartMineStatusResponse:
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    pages_count = await crud.count_pages(db, source_id)
    records_count = await crud.count_records(db, source_id)
    status = _job_statuses.get(source_id, {"job_status": "completed", "updated_at": source.updated_at, "error": None})

    return SmartMineStatusResponse(
        source_id=source_id,
        status=source.status,
        pages_count=pages_count,
        records_count=records_count,
        updated_at=status["updated_at"],
        job_status=status["job_status"],
        error=status["error"],
    )


@router.post("/{source_id}/retry", response_model=SmartMineCreateResponse, status_code=200)
async def retry_smart_mine(source_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> SmartMineCreateResponse:
    source = await crud.get_source(db, source_id)
    if source is None:
        raise HTTPException(status_code=404, detail="Source not found")

    if source.status not in {"failed", "error", "needs_human_review"}:
        raise HTTPException(status_code=422, detail="Source is not in a retryable state")

    _job_statuses[source_id] = {"job_status": "queued", "updated_at": datetime.now(UTC), "error": None}
    background_tasks.add_task(_execute_smart_mine, source_id, source.url)

    return SmartMineCreateResponse(source_id=source_id, status="queued", message="Smart mining retry queued")


@router.get("/templates", response_model=list[SmartTemplateListItem], status_code=200)
async def list_templates() -> list[SmartTemplateListItem]:
    templates = _template_library.list_templates()
    return [SmartTemplateListItem(id=t["id"], name=t.get("name", t["id"]), usage_count=int(t.get("usage_count", 0))) for t in templates]


@router.get("/templates/{template_id}", response_model=dict, status_code=200)
async def get_template(template_id: str) -> dict:
    template = _template_library.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template
