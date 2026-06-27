"""Global exception handlers producing a consistent JSON error envelope."""

from __future__ import annotations

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.core.exceptions import AppException
from app.core.logging import get_logger
from app.schemas.common import ErrorResponse

logger = get_logger(__name__)


def _envelope(
    code: str,
    message: str,
    details: dict | None = None,
) -> dict:
    """Build a JSON-serializable error envelope.

    Args:
        code: Stable machine-readable error code.
        message: Human-readable error message.
        details: Optional structured details for clients.

    Returns:
        Dictionary in the shape of `ErrorResponse`.
    """
    return ErrorResponse(code=code, message=message, details=details or {}).model_dump()


def register_exception_handlers(app: FastAPI) -> None:
    """Attach all custom exception handlers to a FastAPI app.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(AppException)
    async def _handle_app_exception(  # type: ignore[unused-function]
        request: Request, exc: AppException
    ) -> JSONResponse:
        logger.warning(
            "app.exception",
            code=exc.code,
            status_code=exc.status_code,
            message=exc.message,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(  # type: ignore[unused-function]
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        logger.info("request.validation_error", errors=exc.errors())
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_envelope(
                "validation_error",
                "Request validation failed.",
                {"errors": jsonable_encoder(exc.errors())},
            ),
        )

    @app.exception_handler(HTTPException)
    async def _handle_http_exception(  # type: ignore[unused-function]
        request: Request, exc: HTTPException
    ) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=_envelope(
                f"http_{exc.status_code}",
                str(exc.detail) if exc.detail else "HTTP error",
            ),
            headers=getattr(exc, "headers", None),
        )

    @app.exception_handler(SQLAlchemyError)
    async def _handle_database_error(  # type: ignore[unused-function]
        request: Request, exc: SQLAlchemyError
    ) -> JSONResponse:
        logger.exception("database.error")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("database_error", "A database error occurred."),
        )

    @app.exception_handler(Exception)
    async def _handle_unexpected_error(  # type: ignore[unused-function]
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception("unhandled.exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_envelope("internal_error", "An unexpected error occurred."),
        )
