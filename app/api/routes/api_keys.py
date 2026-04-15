import json

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import generate_api_key, mask_api_key
from app.api.deps import get_db
from app.db import crud

router = APIRouter(prefix="/keys", tags=["api-keys"])


class APIKeyCreateRequest(BaseModel):
    name: str
    tenant_id: str = "public"
    permissions: list[str] = ["read"]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_api_key(
    body: APIKeyCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    await crud.ensure_tenant(db, body.tenant_id, name=body.tenant_id)
    raw_key, key_hash = generate_api_key()
    created = await crud.create_api_key(
        db,
        tenant_id=body.tenant_id,
        name=body.name,
        key_prefix=raw_key[:12],
        key_hash=key_hash,
        permissions_json=json.dumps(body.permissions),
    )
    return {
        "id": created.id,
        "tenant_id": created.tenant_id,
        "name": created.name,
        "created_at": created.created_at,
        "raw_key": raw_key,
        "masked_key": mask_api_key(raw_key),
        "enabled": created.enabled,
        "permissions": body.permissions,
    }


@router.get("")
async def list_api_keys(
    tenant_id: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    rows = await crud.list_api_keys(db, tenant_id=tenant_id)
    return {
        "items": [
            {
                "id": row.id,
                "tenant_id": row.tenant_id,
                "name": row.name,
                "key_prefix": row.key_prefix,
                "enabled": row.enabled,
                "usage_count": row.usage_count,
                "created_at": row.created_at,
                "last_used_at": row.last_used_at,
            }
            for row in rows
        ],
        "total": len(rows),
    }


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    db: AsyncSession = Depends(get_db),
):
    deleted = await crud.disable_api_key(db, key_id=key_id, tenant_id=tenant_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="API key not found")
