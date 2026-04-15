import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.rate_limit import rate_limiter
from app.db import crud


@dataclass
class APIPrincipal:
    key_id: str
    tenant_id: str
    permissions: list[str]


def hash_api_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> tuple[str, str]:
    raw = f"ak_live_{secrets.token_urlsafe(32)}"
    return raw, hash_api_key(raw)


def parse_permissions(value: str | None) -> list[str]:
    if not value:
        return ["read"]
    try:
        parsed = json.loads(value)
        if isinstance(parsed, list):
            return [str(item) for item in parsed]
    except json.JSONDecodeError:
        pass
    return ["read"]


async def require_api_key(
    x_api_key: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> APIPrincipal:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header")

    key_hash = hash_api_key(x_api_key)
    key = await crud.get_api_key_by_hash(db, key_hash)
    if key is None or not key.enabled:
        raise HTTPException(status_code=401, detail="Invalid API key")

    decision = rate_limiter.check(key.id)
    if not decision.allowed:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded (100 requests/minute per API key)",
            headers={
                "X-RateLimit-Limit": "100",
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(decision.reset_epoch),
            },
        )

    await crud.touch_api_key(db, key)
    return APIPrincipal(
        key_id=key.id,
        tenant_id=key.tenant_id,
        permissions=parse_permissions(key.permissions_json),
    )


def mask_api_key(raw_key: str) -> str:
    if len(raw_key) <= 10:
        return "***"
    return f"{raw_key[:8]}...{raw_key[-4:]}"


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()
