from collections.abc import Callable
from dataclasses import dataclass

import structlog
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import parse_permissions
from app.api.deps import get_db
from app.config import is_dev_auto_admin_enabled, settings
from app.db import crud

Role = str

ROLE_PERMISSIONS: dict[Role, set[str]] = {
    "admin": {
        "read",
        "write",
        "merge",
        "rerun",
        "schedule",
        "manage_jobs",
        "rollback",
    },
    "reviewer": {"read", "merge", "rerun", "manage_jobs"},
    "viewer": {"read"},
}
logger = structlog.get_logger()


@dataclass
class Principal:
    subject: str
    role: Role
    authenticated_via: str


def _role_from_api_permissions(permissions: list[str]) -> Role:
    permission_set = set(permissions)
    if "admin" in permission_set or "schedule" in permission_set or "rollback" in permission_set:
        return "admin"
    if permission_set.intersection({"write", "merge", "rerun", "manage_jobs"}):
        return "reviewer"
    return "viewer"


async def get_current_principal(
    x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    db: AsyncSession = Depends(get_db),
) -> Principal:
    if x_admin_token:
        if x_admin_token == settings.admin_api_token:
            return Principal(subject="operator", role="admin", authenticated_via="admin_token")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid admin token")

    if x_api_key:
        from app.api.auth import hash_api_key

        api_key = await crud.get_api_key_by_hash(db, hash_api_key(x_api_key))
        if api_key is None or not api_key.enabled:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
        permissions = parse_permissions(api_key.permissions_json)
        return Principal(
            subject=api_key.id,
            role=_role_from_api_permissions(permissions),
            authenticated_via="api_key",
        )

    if is_dev_auto_admin_enabled():
        logger.info(
            "rbac.dev_auto_admin_authenticated",
            environment=settings.environment,
            subject="dev-auto-admin",
            auth_type="development_auto_admin",
        )
        return Principal(
            subject="dev-auto-admin",
            role="admin",
            authenticated_via="development_auto_admin",
        )

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")


def require_permission(permission: str) -> Callable[[Principal], Role]:
    async def dependency(principal: Principal = Depends(get_current_principal)) -> Role:
        permissions = ROLE_PERMISSIONS.get(principal.role)
        if permissions is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unknown principal role")
        if permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{principal.role}' lacks required permission '{permission}'",
            )
        return principal.role

    return dependency
