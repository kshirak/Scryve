"""Authentication and authorization dependencies.

These are foundational pieces wired against the JWT utilities. Concrete user
loading (DB lookup, last-login tracking, etc.) will be added when the auth
module is implemented; for now we expose the decoded token payload and a
role-checking dependency factory.
"""

from __future__ import annotations

from typing import Any, Iterable

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.config import settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.core.security import decode_token
from app.models.user import UserRole

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.api_v1_prefix}/auth/login",
    auto_error=False,
)


def get_current_token_payload(
    token: str | None = Depends(oauth2_scheme),
) -> dict[str, Any]:
    """Validate the bearer token and return its payload.

    Args:
        token: The bearer token extracted from the `Authorization` header.

    Returns:
        The decoded JWT payload.

    Raises:
        UnauthorizedError: When the token is missing or invalid.
    """
    if not token:
        raise UnauthorizedError(
            "Missing bearer token.",
            code="auth.missing_token",
        )
    return decode_token(token, expected_type="access")


def require_roles(*allowed: UserRole):
    """Create a dependency that enforces one of `allowed` roles.

    Usage::

        @router.get(
            "/admin/ping",
            dependencies=[Depends(require_roles(UserRole.ADMIN))],
        )

    Args:
        *allowed: Roles permitted to access the endpoint.

    Returns:
        A FastAPI dependency callable.
    """
    allowed_values: set[str] = {role.value for role in allowed}

    def _dependency(
        payload: dict[str, Any] = Depends(get_current_token_payload),
    ) -> dict[str, Any]:
        role = payload.get("role")
        if role not in allowed_values:
            raise ForbiddenError(
                "Insufficient role for this resource.",
                code="auth.insufficient_role",
                details={"required": sorted(allowed_values), "actual": role},
            )
        return payload

    return _dependency


def get_allowed_roles() -> Iterable[UserRole]:
    """Return the canonical list of roles (helper for docs/admin tooling)."""
    return list(UserRole)
