"""SQLAlchemy engine and session factory.

Synchronous SQLAlchemy is used here because it has the broadest ecosystem
support (Alembic, mature drivers). Endpoints stay `async` and call into the
sync session from the threadpool via FastAPI's `Depends`.
"""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


def _build_engine() -> Engine:
    """Create the SQLAlchemy engine using values from settings.

    Returns:
        A configured SQLAlchemy `Engine` with sensible pool defaults.
    """
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        future=True,
        echo=False,
    )


engine: Engine = _build_engine()

SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    class_=Session,
)


def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and ensure it is closed on exit.

    Designed to be used with FastAPI's `Depends`:

        @router.get("/things")
        def list_things(db: Session = Depends(get_db)): ...

    Yields:
        An active SQLAlchemy `Session`.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
