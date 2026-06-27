"""Generic repository implementing common persistence operations.

Concrete repositories should subclass `BaseRepository` and bind it to a
specific ORM model. Services depend on repository abstractions, never on the
SQLAlchemy session directly, to keep the data-access concerns isolated.
"""

from __future__ import annotations

from typing import Any, Generic, Sequence, Type, TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Reusable CRUD operations for a single SQLAlchemy model."""

    model: Type[ModelT]

    def __init__(self, db: Session) -> None:
        """Initialize the repository.

        Args:
            db: The active SQLAlchemy session.
        """
        self.db = db

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------
    def get(self, id_: Any) -> ModelT | None:
        """Fetch a single row by primary key.

        Args:
            id_: The primary-key value to look up.

        Returns:
            The model instance or None when not found.
        """
        return self.db.get(self.model, id_)

    def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        """Fetch a paginated list of rows.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip.

        Returns:
            A sequence of model instances.
        """
        stmt = select(self.model).limit(limit).offset(offset)
        return self.db.execute(stmt).scalars().all()

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------
    def add(self, instance: ModelT, *, commit: bool = True) -> ModelT:
        """Persist a new instance.

        Args:
            instance: The model instance to add.
            commit: Whether to commit the transaction immediately.

        Returns:
            The persisted (and refreshed) instance.
        """
        self.db.add(instance)
        if commit:
            self.db.commit()
            self.db.refresh(instance)
        else:
            self.db.flush()
        return instance

    def delete(self, instance: ModelT, *, commit: bool = True) -> None:
        """Delete an existing instance.

        Args:
            instance: The model instance to remove.
            commit: Whether to commit the transaction immediately.
        """
        self.db.delete(instance)
        if commit:
            self.db.commit()
