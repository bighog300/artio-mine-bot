from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.db import crud

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
async def get_usage(
    tenant_id: str | None = None,
    api_key_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    return await crud.get_usage_summary(db, tenant_id=tenant_id, api_key_id=api_key_id)
