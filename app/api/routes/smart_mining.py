from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.smart_miner import SmartMiner
from app.ai.openai_client import OpenAIClient
from app.ai.templates import TemplateLibrary
from app.api.deps import get_db
from app.api.rbac import Principal, get_current_principal
from app.db import crud
from app.db.database import AsyncSessionLocal
from app.config import settings

router = APIRouter(prefix="/smart-mine", tags=["smart-mining"])
logger = structlog.get_logger()

_miner: SmartMiner | None = None
_template_library = TemplateLibrary()
_job_statuses: dict[str, dict] = {}


def _get_miner() -> SmartMiner:
    global _miner
    if _miner is None:
        _miner = SmartMiner(openai_client=OpenAIClient(api_key=settings.openai_api_key or "test"))
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
    helpful_error: str | None = None


class SmartTemplateListItem(BaseModel):
    id: str
    name: str
    usage_count: int = 0


class SmartMineMetricsResponse(BaseModel):
    cache: dict
    usage_totals: dict[str, float]
    usage_by_operation: dict[str, dict[str, float]]
    daily_cost_report: dict[str, dict[str, float]]
    recent_cost_alerts: list[dict]


def _helpful_error_message(error: str | None) -> str | None:
    if not error:
        return None
    return "We couldn’t finish Smart Mode. Please retry, or switch to Guided Mode for step-by-step setup."


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
        logger.exception("smart_mine_background_failed", source_id=source_id, technical_error=str(exc))
        _job_statuses[source_id] = {
            "job_status": "failed",
            "updated_at": datetime.now(UTC),
            "error": "Smart Mode couldn’t complete for this site right now.",
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
        helpful_error=_helpful_error_message(status["error"]),
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


@router.get("/metrics", response_model=SmartMineMetricsResponse, status_code=200)
async def get_smart_mine_metrics(principal: Principal = Depends(get_current_principal)) -> SmartMineMetricsResponse:
    if principal.role != "admin":
        raise HTTPException(status_code=403, detail="This dashboard is available to admins only.")
    miner = _get_miner()
    return SmartMineMetricsResponse(
        cache=await miner.cache_stats(),
        usage_totals=miner.openai_client.get_usage_totals(),
        usage_by_operation=miner.openai_client.get_operation_totals(),
        daily_cost_report=miner.openai_client.get_daily_cost_report(),
        recent_cost_alerts=miner.recent_cost_alerts(),
    )
