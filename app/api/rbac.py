from collections.abc import Callable

from fastapi import Header, HTTPException

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


def require_permission(permission: str) -> Callable[[str | None], Role]:
    async def dependency(x_role: str | None = Header(default="admin")) -> Role:
        role = (x_role or "admin").strip().lower()
        permissions = ROLE_PERMISSIONS.get(role)
        if permissions is None:
            raise HTTPException(status_code=403, detail=f"Unknown role '{role}'")
        if permission not in permissions:
            raise HTTPException(
                status_code=403,
                detail=f"Role '{role}' lacks required permission '{permission}'",
            )
        return role

    return dependency
