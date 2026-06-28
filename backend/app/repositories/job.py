"""Job-aggregate persistence (Phase 3 — Job Intelligence)."""

from __future__ import annotations

import uuid
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.job import Job, JobEmbedding
from app.repositories.base import BaseRepository


class JobRepository(BaseRepository[Job]):
    """CRUD for :class:`Job` plus a few list/embedding helpers."""

    model = Job

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    # ------------------------------------------------------------------
    # Listing
    # ------------------------------------------------------------------
    def list_recent(self, *, limit: int = 50, offset: int = 0) -> Sequence[Job]:
        """Return jobs ordered by most recent first."""
        stmt = (
            select(Job)
            .order_by(Job.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return self.db.execute(stmt).scalars().all()

    def get_with_embedding(self, job_id: uuid.UUID) -> Job | None:
        """Eager-fetch a job including its embedding."""
        return self.db.get(Job, job_id)

    # ------------------------------------------------------------------
    # Embedding lifecycle
    # ------------------------------------------------------------------
    def upsert_embedding(
        self,
        job: Job,
        *,
        vector: list[float],
        model_name: str,
        dimension: int,
        source_text: str,
        commit: bool = True,
    ) -> JobEmbedding:
        """Insert or replace the embedding row for a job.

        Args:
            job: The persisted :class:`Job` (must already have an id).
            vector: L2-normalized embedding vector.
            model_name: Embedding-backend identifier.
            dimension: Vector length (kept in the row for safety).
            source_text: The text that was actually embedded.
            commit: Commit the transaction immediately when True.

        Returns:
            The persisted :class:`JobEmbedding` instance.
        """
        existing = job.embedding
        if existing is not None:
            existing.vector = vector
            existing.model_name = model_name
            existing.dimension = dimension
            existing.source_text = source_text
            embedding = existing
        else:
            embedding = JobEmbedding(
                job_id=job.id,
                vector=vector,
                model_name=model_name,
                dimension=dimension,
                source_text=source_text,
            )
            self.db.add(embedding)
            job.embedding = embedding

        if commit:
            self.db.commit()
            self.db.refresh(embedding)
        else:
            self.db.flush()
        return embedding

    # ------------------------------------------------------------------
    # Convenience finders
    # ------------------------------------------------------------------
    def search_by_title(self, query: str, *, limit: int = 20) -> Sequence[Job]:
        """Case-insensitive ILIKE search on the job title."""
        stmt = (
            select(Job)
            .where(Job.title.ilike(f"%{query}%"))
            .order_by(Job.created_at.desc())
            .limit(limit)
        )
        return self.db.execute(stmt).scalars().all()


__all__ = ["JobRepository"]
