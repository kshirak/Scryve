"""Custom application exception hierarchy.

All domain-level errors should inherit from `AppException` so the global
exception handler can serialize them into a consistent JSON envelope.
"""

from __future__ import annotations

from typing import Any

from fastapi import status


class AppException(Exception):
    """Base class for all application-level exceptions.

    Attributes:
        status_code: HTTP status code returned to the client.
        message: Human-readable error message.
        code: Stable machine-readable error code (e.g. `auth.invalid_token`).
        details: Optional structured details for clients.
    """

    status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    code: str = "internal_error"
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.message = message or self.message
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource could not be located."""

    status_code = status.HTTP_404_NOT_FOUND
    code = "not_found"
    message = "Resource not found."


class ValidationError(AppException):
    """Domain validation failed (distinct from request schema validation)."""

    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    code = "validation_error"
    message = "Validation failed."


class ConflictError(AppException):
    """Operation conflicts with the current state of the resource."""

    status_code = status.HTTP_409_CONFLICT
    code = "conflict"
    message = "Resource conflict."


class UnauthorizedError(AppException):
    """Authentication is missing or invalid."""

    status_code = status.HTTP_401_UNAUTHORIZED
    code = "unauthorized"
    message = "Authentication required."


class ForbiddenError(AppException):
    """The caller is authenticated but lacks the required permissions."""

    status_code = status.HTTP_403_FORBIDDEN
    code = "forbidden"
    message = "You do not have permission to perform this action."
