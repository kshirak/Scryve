"""FastAPI application entrypoint.

This module wires together configuration, logging, middleware, exception
handlers and the versioned API router. Keep this file thin: it should only
*compose* the application, never define business logic.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.v1 import api_router as api_v1_router
from app.config import settings
from app.core.logging import configure_logging, get_logger
from app.middleware import RequestLoggingMiddleware, register_exception_handlers


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure cross-cutting concerns on startup.

    Args:
        app: The FastAPI application instance.
    """
    configure_logging()
    logger = get_logger(__name__)
    logger.info(
        "app.startup",
        service=settings.app_name,
        version=__version__,
        environment=settings.app_env,
    )
    yield
    logger.info("app.shutdown")


def create_app() -> FastAPI:
    """Application factory.

    Returns:
        A fully configured FastAPI application.
    """
    app = FastAPI(
        title=f"{settings.app_name} API",
        description=(
            "Scryve — AI-powered Talent Intelligence platform.\n\n"
            "Backend foundation: authentication, configuration, database, "
            "and health checks."
        ),
        version=__version__,
        debug=settings.app_debug,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # --- CORS ---
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["x-request-id"],
    )

    # --- Custom middleware ---
    app.add_middleware(RequestLoggingMiddleware)

    # --- Exception handlers ---
    register_exception_handlers(app)

    # --- Routers ---
    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        """Root endpoint pointing developers to the API docs."""
        return {
            "service": settings.app_name,
            "version": __version__,
            "docs": "/docs",
            "api": settings.api_v1_prefix,
        }

    return app


app = create_app()
