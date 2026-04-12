import httpx
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.schemas import (
    ImageValidationResult,
    ValidateImagesRequest,
    ValidateImagesResponse,
)
from app.db import crud

router = APIRouter(prefix="/images", tags=["images"])


@router.get("")
async def list_images(
    record_id: str | None = None,
    source_id: str | None = None,
    image_type: str | None = None,
    is_valid: bool | None = None,
    skip: int = 0,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    images = await crud.list_images(
        db,
        record_id=record_id,
        source_id=source_id,
        image_type=image_type,
        is_valid=is_valid,
        skip=skip,
        limit=limit,
    )
    items = [
        {
            "id": img.id,
            "url": img.url,
            "image_type": img.image_type,
            "alt_text": img.alt_text,
            "confidence": img.confidence,
            "is_valid": img.is_valid,
            "mime_type": img.mime_type,
            "width": img.width,
            "height": img.height,
            "source_id": img.source_id,
            "record_id": img.record_id,
            "created_at": img.created_at,
        }
        for img in images
    ]
    return {"items": items, "total": len(items), "skip": skip, "limit": limit}


@router.post("/validate", response_model=ValidateImagesResponse)
async def validate_images(body: ValidateImagesRequest):
    results: list[ImageValidationResult] = []
    async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
        for url in body.urls:
            try:
                resp = await client.head(url)
                content_type = resp.headers.get("content-type", "")
                is_valid = resp.status_code < 400 and content_type.startswith("image/")
                results.append(
                    ImageValidationResult(
                        url=url,
                        is_valid=is_valid,
                        mime_type=content_type.split(";")[0].strip() if content_type else None,
                        status_code=resp.status_code,
                    )
                )
            except Exception as exc:
                results.append(
                    ImageValidationResult(url=url, is_valid=False, error=str(exc))
                )
    return ValidateImagesResponse(results=results)
