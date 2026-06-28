"""Job and JobEmbedding ORM models (Phase 3 — Job Intelligence).

A job is persisted in two related rows:

* :class:`Job` — the canonical record. Holds the raw description plus
  every structured field produced by :class:`~app.intelligence.parsers.job_extractor.JobExtractor`.
* :class:`JobEmbedding` — the vector representation of the job, stored
  separately so we can swap embedding models or rebuild the FAISS index
  without touching the canonical job row.

Both tables use the project-wide :class:`Base` and :class:`TimestampMixin`
so Alembic autogenerate detects them and so ``updated_at`` is always
populated.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import (
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin


class Job(Base, TimestampMixin):
    """A persisted job description with structured intelligence."""

    __tablename__ = "jobs"

    # --- Identity ---
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)

    # --- Context ---
    industry: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(
        String(40), nullable=True
    )
    experience_min_years: Mapped[Optional[float]] = mapped_column(nullable=True)
    experience_max_years: Mapped[Optional[float]] = mapped_column(nullable=True)
    locations: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    # --- Skill buckets (all normalized via SkillNormalizer) ---
    required_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    preferred_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    soft_skills: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    programming_languages: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    tools_frameworks: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    domain_knowledge: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    # --- Narrative buckets ---
    responsibilities: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    qualifications: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    education_requirements: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    disqualifiers: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )
    extracted_keywords: Mapped[list[str]] = mapped_column(
        ARRAY(String), nullable=False, server_default="{}"
    )

    # --- Provenance ---
    source_format: Mapped[str] = mapped_column(
        String(20), nullable=False, server_default="text"
    )
    raw_extraction: Mapped[dict] = mapped_column(
        JSONB, nullable=False, server_default="{}"
    )

    # --- Relationships ---
    embedding: Mapped[Optional["JobEmbedding"]] = relationship(
        "JobEmbedding",
        back_populates="job",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="joined",
    )

    __table_args__ = (
        Index("ix_jobs_title_trgm_like", "title"),
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<Job id={self.id} title={self.title!r}>"


class JobEmbedding(Base, TimestampMixin):
    """A vector embedding for a single job description.

    Each job has at most one embedding. Re-embedding a job replaces this
    row (rather than appending) so the FAISS index can be rebuilt by
    streaming the table.
    """

    __tablename__ = "job_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    job_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("jobs.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    model_name: Mapped[str] = mapped_column(String(120), nullable=False)
    dimension: Mapped[int] = mapped_column(Integer, nullable=False)
    vector: Mapped[list[float]] = mapped_column(
        ARRAY(Float),
        nullable=False,
    )
    source_text: Mapped[str] = mapped_column(Text, nullable=False)

    job: Mapped[Job] = relationship("Job", back_populates="embedding")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<JobEmbedding job_id={self.job_id} "
            f"model={self.model_name} dim={self.dimension}>"
        )
