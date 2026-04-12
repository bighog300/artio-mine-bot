from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_ai_client, get_db
from app.api.schemas import PageDetailResponse, PageResponse
from app.db import crud

router = APIRouter(prefix="/pages", tags=["pages"])


def _page_to_dict(page, record_count: int = 0) -> dict:
    return {
        "id": page.id,
        "source_id": page.source_id,
        "url": page.url,
        "page_type": page.page_type,
        "status": page.status,
        "title": page.title,
        "depth": page.depth,
        "fetch_method": page.fetch_method,
        "crawled_at": page.crawled_at,
        "record_count": record_count,
    }


@router.get("")
async def list_pages(
    source_id: str | None = None,
    status: str | None = None,
    page_type: str | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    pages = await crud.list_pages(
        db, source_id=source_id, status=status, page_type=page_type, skip=skip, limit=limit
    )
    items = [_page_to_dict(p) for p in pages]
    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.get("/{page_id}")
async def get_page(page_id: str, db: AsyncSession = Depends(get_db)):
    page = await crud.get_page(db, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    return {
        **_page_to_dict(page),
        "html": page.html,
        "original_url": page.original_url,
        "error_message": page.error_message,
        "created_at": page.created_at,
        "extracted_at": page.extracted_at,
    }


@router.post("/{page_id}/reclassify")
async def reclassify_page(page_id: str, db: AsyncSession = Depends(get_db)):
    page = await crud.get_page(db, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if not page.html:
        raise HTTPException(status_code=400, detail="Page has no HTML to classify")

    from app.ai.classifier import classify_page

    ai_client = get_ai_client()
    result = await classify_page(url=page.url, html=page.html, ai_client=ai_client)
    updated = await crud.update_page(db, page_id, page_type=result.page_type, status="classified")
    return _page_to_dict(updated)


@router.post("/{page_id}/reextract")
async def reextract_page(page_id: str, db: AsyncSession = Depends(get_db)):
    page = await crud.get_page(db, page_id)
    if not page:
        raise HTTPException(status_code=404, detail="Page not found")
    if not page.html:
        raise HTTPException(status_code=400, detail="Page has no HTML to extract")

    from app.pipeline.runner import PipelineRunner

    ai_client = get_ai_client()
    runner = PipelineRunner(db=db, ai_client=ai_client)
    record = await runner.run_extraction_for_page(page)
    if record is None:
        raise HTTPException(status_code=422, detail="Could not extract record from this page")
    return {"id": record.id, "record_type": record.record_type, "status": record.status}
