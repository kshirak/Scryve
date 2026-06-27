"""Security primitives: password hashing and JWT token utilities.

This module deliberately contains *no* business logic. Higher-level services
(e.g. an auth service implemented later) should orchestrate user lookup and
permission checks on top of these primitives.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings
from app.core.exceptions import UnauthorizedError

TokenType = Literal["access", "refresh"]

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ----------------------------------------------------------------------
# Password hashing
# ----------------------------------------------------------------------
def hash_password(password: str) -> str:
    """Hash a plaintext password using bcrypt.

    Args:
        password: The plaintext password to hash.

    Returns:
        The bcrypt hash, safe to persist in the database.
    """
    return _pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plaintext password against a bcrypt hash.

    Args:
        plain_password: The plaintext password supplied by the user.
        hashed_password: The previously stored bcrypt hash.

    Returns:
        True if the password matches, False otherwise.
    """
    return _pwd_context.verify(plain_password, hashed_password)


# ----------------------------------------------------------------------
# JWT
# ----------------------------------------------------------------------
def _create_token(
    subject: str | int,
    token_type: TokenType,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """Build and sign a JWT with the configured secret/algorithm.

    Args:
        subject: The token subject, typically the user id.
        token_type: Either `access` or `refresh`.
        expires_delta: Lifetime of the token.
        extra_claims: Additional claims to merge into the payload
            (e.g. ``{"role": "recruiter"}``).

    Returns:
        The encoded JWT as a string.
    """
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "type": token_type,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a short-lived access token.

    Args:
        subject: The token subject (typically user id).
        extra_claims: Optional additional claims (e.g. role).
        expires_delta: Override for the default token lifetime.

    Returns:
        Encoded JWT access token.
    """
    delta = expires_delta or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    return _create_token(subject, "access", delta, extra_claims)


def create_refresh_token(
    subject: str | int,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Create a long-lived refresh token.

    Args:
        subject: The token subject (typically user id).
        extra_claims: Optional additional claims.
        expires_delta: Override for the default token lifetime.

    Returns:
        Encoded JWT refresh token.
    """
    delta = expires_delta or timedelta(days=settings.jwt_refresh_token_expire_days)
    return _create_token(subject, "refresh", delta, extra_claims)


def decode_token(token: str, expected_type: TokenType | None = None) -> dict[str, Any]:
    """Decode and validate a JWT.

    Args:
        token: The encoded JWT.
        expected_type: If provided, the token's `type` claim must match.

    Returns:
        The decoded payload as a dictionary.

    Raises:
        UnauthorizedError: If the token is invalid, expired, or of the wrong
            type.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError as exc:  # pragma: no cover - exercised via auth tests later
        raise UnauthorizedError(
            "Invalid or expired token.",
            code="auth.invalid_token",
        ) from exc

    if expected_type and payload.get("type") != expected_type:
        raise UnauthorizedError(
            f"Expected a {expected_type} token.",
            code="auth.wrong_token_type",
        )

    return payload
