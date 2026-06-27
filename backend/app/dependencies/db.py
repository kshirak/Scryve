"""Database-related FastAPI dependencies."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.database.session import get_db


def get_db_session() -> Generator[Session, None, None]:
    """Provide a request-scoped SQLAlchemy session.

    Thin wrapper around `app.database.session.get_db` so endpoint signatures
    depend on `app.dependencies` rather than reaching directly into the
    database package.

    Yields:
        An active SQLAlchemy `Session`.
    """
    yield from get_db()
