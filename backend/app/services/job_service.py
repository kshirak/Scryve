"""Job-intelligence service (Phase 3).

The service is the *single entry point* used by the API layer and by
Phase 4/5 consumers. It orchestrates the three concerns described in
the Phase-3 spec:

1. **Extraction** — convert raw JD text into structured fields via
   :class:`app.intelligence.parsers.job_extractor.JobExtractor`.
2. **Persistence** — store the canonical record through
   :class:`app.repositories.job.JobRepository`.
3. **Embedding** — generate and persist the vector representation via
   :class:`app.intelligence.embeddings.Embedder`.

Public methods deliberately match the Phase-3 contract:

* :meth:`JobService.create_job_profile`
* :meth:`JobService.extract_job_skills`
* :meth:`JobService.generate_job_embedding`
* :meth:`JobService.get_job_requirements`
"""

from __future__ import annotations

import uuid
from typing import Iterable, Optional

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.intelligence.embeddings import Embedder, build_embedder
from app.intelligence.parsers.job_extractor import (
    JobExtraction,
    JobExtractor,
)
from app.models.job import Job, JobEmbedding
from app.repositories.job import JobRepository
from app.schemas.job import JobCreate, JobRequirements

logger = get_logger(__name__)


class JobService:
    """High-level operations for the job-intelligence module."""

    def __init__(
        self,
        db: Session,
        *,
        extractor: JobExtractor | None = None,
        embedder: Embedder | None = None,
        repository: JobRepository | None = None,
    ) -> None:
        """Build a service instance.

        Args:
            db: Active SQLAlchemy session (request-scoped).
            extractor: Optional preconfigured extractor (defaults are fine
                for most callers).
            embedder: Optional preconfigured embedder. Defaults to
                :func:`build_embedder` which honours the env config.
            repository: Optional repository injection point (tests).
        """
        self.db = db
        self.extractor = extractor or JobExtractor()
        self._embedder = embedder
        self.repository = repository or JobRepository(db)

    # ------------------------------------------------------------------
    # Public API — matches Phase 3 contract
    # ------------------------------------------------------------------
    def create_job_profile(self, payload: JobCreate) -> Job:
        """Extract, persist, and (optionally) embed a job description.

        Args:
            payload: The :class:`JobCreate` request body.

        Returns:
            The persisted :class:`Job` row, with ``embedding`` populated
            when ``payload.generate_embedding`` is True.
        """
        extraction = self.extractor.extract(
            payload.description, title=payload.title
        )
        job = self._materialize_job(payload, extraction)
        self.repository.add(job)

        logger.info(
            "job.created",
            job_id=str(job.id),
            title=job.title,
            required_skill_count=len(job.required_skills),
            preferred_skill_count=len(job.preferred_skills),
        )

        if payload.generate_embedding:
            self.generate_job_embedding(job.id)

        # Re-fetch so the embedding relationship is populated.
        refreshed = self.repository.get_with_embedding(job.id)
        return refreshed or job

    def extract_job_skills(
        self,
        text: str,
        *,
        title: Optional[str] = None,
    ) -> JobExtraction:
        """Run the extraction pipeline without persisting the result.

        Useful for "preview" endpoints and the matching layer in Phase 4
        when a JD has not yet been saved.

        Args:
            text: The JD body.
            title: Optional human-curated title override.

        Returns:
            A :class:`JobExtraction` with every structured field populated.
        """
        return self.extractor.extract(text, title=title)

    def generate_job_embedding(self, job_id: uuid.UUID) -> JobEmbedding:
        """(Re)generate and persist the embedding for an existing job.

        Args:
            job_id: Primary key of the job to embed.

        Returns:
            The persisted :class:`JobEmbedding` row.

        Raises:
            NotFoundError: When the job does not exist.
        """
        job = self._require_job(job_id)
        source_text = self._embedding_source_text(job)
        result = self.embedder.embed(source_text)
        embedding = self.repository.upsert_embedding(
            job,
            vector=result.vector,
            model_name=result.model_name,
            dimension=result.dimension,
            source_text=source_text,
        )
        logger.info(
            "job.embedding.upserted",
            job_id=str(job_id),
            model=result.model_name,
            dimension=result.dimension,
        )
        return embedding

    def get_job_requirements(self, job_id: uuid.UUID) -> JobRequirements:
        """Return the matching-ready requirement view for a job.

        Args:
            job_id: Primary key of the job.

        Returns:
            A :class:`JobRequirements` schema instance.

        Raises:
            NotFoundError: When the job does not exist.
        """
        job = self._require_job(job_id)
        return JobRequirements(
            job_id=job.id,
            title=job.title,
            role=job.role,
            experience_min_years=job.experience_min_years,
            experience_max_years=job.experience_max_years,
            experience_level=job.experience_level,
            required_skills=list(job.required_skills),
            preferred_skills=list(job.preferred_skills),
            soft_skills=list(job.soft_skills),
            programming_languages=list(job.programming_languages),
            tools_frameworks=list(job.tools_frameworks),
            domain_knowledge=list(job.domain_knowledge),
            education_requirements=list(job.education_requirements),
            extracted_keywords=list(job.extracted_keywords),
            disqualifiers=list(job.disqualifiers),
            locations=list(job.locations),
        )

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------
    def get_job(self, job_id: uuid.UUID) -> Job:
        """Return a persisted :class:`Job` or raise :class:`NotFoundError`."""
        return self._require_job(job_id)

    def list_jobs(self, *, limit: int = 50, offset: int = 0) -> Iterable[Job]:
        """List recently created jobs."""
        return self.repository.list_recent(limit=limit, offset=offset)

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    @property
    def embedder(self) -> Embedder:
        """Lazily build the embedder so unrelated calls don't pay the cost."""
        if self._embedder is None:
            self._embedder = build_embedder()
        return self._embedder

    def _require_job(self, job_id: uuid.UUID) -> Job:
        job = self.repository.get_with_embedding(job_id)
        if job is None:
            raise NotFoundError(
                f"Job {job_id} not found.",
                code="job.not_found",
                details={"job_id": str(job_id)},
            )
        return job

    @staticmethod
    def _materialize_job(payload: JobCreate, extraction: JobExtraction) -> Job:
        """Build a fresh :class:`Job` ORM instance from an extraction."""
        title = (
            payload.title
            or extraction.title
            or extraction.role
            or "Untitled Role"
        )
        return Job(
            title=title,
            description=payload.description,
            role=extraction.role,
            industry=extraction.industry,
            experience_level=extraction.experience_level,
            experience_min_years=extraction.experience_min_years,
            experience_max_years=extraction.experience_max_years,
            locations=list(extraction.locations),
            required_skills=list(extraction.required_skills),
            preferred_skills=list(extraction.preferred_skills),
            soft_skills=list(extraction.soft_skills),
            programming_languages=list(extraction.programming_languages),
            tools_frameworks=list(extraction.tools_frameworks),
            domain_knowledge=list(extraction.domain_knowledge),
            responsibilities=list(extraction.responsibilities),
            qualifications=list(extraction.qualifications),
            education_requirements=list(extraction.education_requirements),
            disqualifiers=list(extraction.disqualifiers),
            extracted_keywords=list(extraction.extracted_keywords),
            source_format=payload.source_format,
            raw_extraction=extraction.model_dump(mode="json"),
        )

    @staticmethod
    def _embedding_source_text(job: Job) -> str:
        """Compose the text that should be fed to the embedder.

        Combines the title, role, full description, and the high-signal
        keyword bag so the resulting vector captures both the narrative
        and the structured concepts the extractor surfaced.
        """
        parts: list[str] = []
        if job.title:
            parts.append(f"Title: {job.title}")
        if job.role and job.role != job.title:
            parts.append(f"Role: {job.role}")
        if job.experience_level:
            parts.append(f"Level: {job.experience_level}")
        if job.required_skills:
            parts.append("Required skills: " + ", ".join(job.required_skills))
        if job.preferred_skills:
            parts.append("Preferred skills: " + ", ".join(job.preferred_skills))
        if job.domain_knowledge:
            parts.append("Domain: " + ", ".join(job.domain_knowledge))
        if job.description:
            parts.append(job.description)
        return "\n".join(parts).strip()


__all__ = ["JobService"]
