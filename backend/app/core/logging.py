"""Structured logging configuration using structlog.

Provides a single `configure_logging()` entrypoint that should be called once
during application startup. After configuration, any module can obtain a logger
via `get_logger(__name__)` and emit structured key/value records.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.config import settings


def configure_logging() -> None:
    """Configure stdlib logging and structlog with sensible defaults.

    The configuration emits JSON in production for log aggregators, and a
    colored human-readable format in development.
    """
    log_level = getattr(logging, settings.log_level, logging.INFO)

    # Reset stdlib root logger so uvicorn/alembic propagate through structlog.
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if settings.is_production:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[*shared_processors, renderer],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a structlog logger bound to the given name.

    Args:
        name: Logical logger name, usually `__name__`.

    Returns:
        A structlog `BoundLogger` ready for structured logging.
    """
    return structlog.get_logger(name)
