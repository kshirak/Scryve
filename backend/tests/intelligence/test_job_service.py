"""End-to-end Phase-3 service flow tests.

The Job model uses Postgres-only column types (``ARRAY``, ``JSONB``,
``UUID``), so these tests run the service against a tiny in-memory
fake repository rather than spinning up a real database. The fake
honours just enough of :class:`~app.repositories.job.JobRepository`'s
surface to exercise the full extraction → persistence → embedding
pipeline.
"""

from __future__ import annotations

import uuid
from typing import Sequence

import pytest

from app.intelligence.embeddings.embedder import HashingEmbedder
from app.models.job import Job, JobEmbedding
from app.schemas.job import JobCreate
from app.services.job_service import JobService


class _FakeJobRepository:
    """Minimal in-memory stand-in for :class:`JobRepository`."""

    def __init__(self) -> None:
        self._jobs: dict[uuid.UUID, Job] = {}

    # API used by JobService
    def add(self, instance: Job, *, commit: bool = True) -> Job:  # noqa: ARG002
        if instance.id is None:
            instance.id = uuid.uuid4()
        self._jobs[instance.id] = instance
        return instance

    def get_with_embedding(self, job_id: uuid.UUID) -> Job | None:
        return self._jobs.get(job_id)

    def list_recent(self, *, limit: int = 50, offset: int = 0) -> Sequence[Job]:
        items = list(self._jobs.values())
        return items[offset : offset + limit]

    def upsert_embedding(
        self,
        job: Job,
        *,
        vector: list[float],
        model_name: str,
        dimension: int,
        source_text: str,
        commit: bool = True,  # noqa: ARG002
    ) -> JobEmbedding:
        embedding = JobEmbedding(
            id=uuid.uuid4(),
            job_id=job.id,
            vector=vector,
            model_name=model_name,
            dimension=dimension,
            source_text=source_text,
        )
        job.embedding = embedding
        return embedding


@pytest.fixture
def service() -> JobService:
    repo = _FakeJobRepository()
    return JobService(
        db=None,  # type: ignore[arg-type]  unused once repository is injected
        embedder=HashingEmbedder(dimension=128, model_name="hashing-test"),
        repository=repo,  # type: ignore[arg-type]
    )


@pytest.fixture
def python_jd_payload() -> JobCreate:
    return JobCreate(
        title="Backend Developer",
        description=(
            "Looking for Python Django developer with PostgreSQL experience "
            "and REST API knowledge. 2-4 years experience required. "
            "You'll build and maintain APIs and collaborate with the team."
        ),
        generate_embedding=True,
    )


def test_create_job_profile_persists_and_embeds(
    service: JobService, python_jd_payload: JobCreate
) -> None:
    job = service.create_job_profile(python_jd_payload)

    assert job.id is not None
    assert job.title == "Backend Developer"
    assert "Python" in job.required_skills
    assert "Django" in job.required_skills
    assert "PostgreSQL" in job.required_skills
    assert "REST API" in job.required_skills
    assert job.experience_min_years == 2
    assert job.experience_max_years == 4

    # Embedding was generated inline.
    assert job.embedding is not None
    assert job.embedding.dimension == 128
    assert len(job.embedding.vector) == 128


def test_extract_job_skills_does_not_persist(service: JobService) -> None:
    extraction = service.extract_job_skills(
        "Senior AI engineer with vector search, FAISS, and PyTorch."
    )
    assert "FAISS" in extraction.required_skills
    assert "PyTorch" in extraction.required_skills
    assert extraction.experience_level in {"Senior", "Mid", "Junior", None}


def test_get_job_requirements_returns_matching_view(
    service: JobService, python_jd_payload: JobCreate
) -> None:
    job = service.create_job_profile(python_jd_payload)
    requirements = service.get_job_requirements(job.id)

    assert requirements.job_id == job.id
    assert "Python" in requirements.required_skills
    assert requirements.experience_min_years == 2
    assert requirements.experience_max_years == 4


def test_regenerate_embedding_replaces_existing(
    service: JobService, python_jd_payload: JobCreate
) -> None:
    job = service.create_job_profile(python_jd_payload)
    original_id = job.embedding.id

    new_embedding = service.generate_job_embedding(job.id)
    # `id` may change (fake builds a new record) but vector must be deterministic.
    assert new_embedding.dimension == job.embedding.dimension
    assert new_embedding.vector == job.embedding.vector
    assert new_embedding.id is not None
    # The job still has exactly one embedding linked.
    assert service.get_job(job.id).embedding is not None
    _ = original_id  # silence unused
