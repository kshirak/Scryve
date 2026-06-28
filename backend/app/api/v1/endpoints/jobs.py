"""HTTP routes for the Job Intelligence module (Phase 3)."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.dependencies import get_db_session
from app.schemas.job import (
    EmbeddingRegenerateResponse,
    JobCreate,
    JobEmbeddingDetailRead,
    JobExtractionResponse,
    JobListItem,
    JobRead,
    JobRequirements,
    RawExtractionView,
)
from app.services import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])
logger = get_logger(__name__)


def get_job_service(
    db: Annotated[Session, Depends(get_db_session)],
) -> JobService:
    """FastAPI dependency that constructs a request-scoped :class:`JobService`."""
    return JobService(db)


JobServiceDep = Annotated[JobService, Depends(get_job_service)]


# ----------------------------------------------------------------------
# Extraction-only (no DB write)
# ----------------------------------------------------------------------
@router.post(
    "/extract",
    response_model=JobExtractionResponse,
    status_code=status.HTTP_200_OK,
    summary="Extract structured intelligence from a JD without saving it.",
)
async def extract_job(
    payload: JobCreate,
    service: JobServiceDep,
) -> JobExtractionResponse:
    """Run the Phase-3 extraction pipeline without persisting anything.

    Useful as a "preview" endpoint for UIs that want to show recruiters
    what the platform will store before they commit.
    """
    extraction = service.extract_job_skills(
        payload.description, title=payload.title
    )
    return JobExtractionResponse(
        title=extraction.title,
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
    )


# ----------------------------------------------------------------------
# Create
# ----------------------------------------------------------------------
@router.post(
    "",
    response_model=JobRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job and store its extracted intelligence.",
)
async def create_job(
    payload: JobCreate,
    service: JobServiceDep,
) -> JobRead:
    """Extract, persist, and (optionally) embed a new job description."""
    job = service.create_job_profile(payload)
    return JobRead.model_validate(job)


# ----------------------------------------------------------------------
# Read
# ----------------------------------------------------------------------
@router.get(
    "",
    response_model=list[JobListItem],
    summary="List recently created jobs.",
)
async def list_jobs(
    service: JobServiceDep,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> list[JobListItem]:
    """Return the most recently created jobs in compact form."""
    jobs = service.list_jobs(limit=limit, offset=offset)
    return [JobListItem.model_validate(job) for job in jobs]


@router.get(
    "/{job_id}",
    response_model=JobRead,
    summary="Fetch a single job by id.",
)
async def get_job(
    job_id: uuid.UUID,
    service: JobServiceDep,
) -> JobRead:
    """Return the full Phase-3 record for a single job."""
    job = service.get_job(job_id)
    return JobRead.model_validate(job)


@router.get(
    "/{job_id}/requirements",
    response_model=JobRequirements,
    summary="Return the matching-ready requirement view for a job.",
)
async def get_job_requirements(
    job_id: uuid.UUID,
    service: JobServiceDep,
) -> JobRequirements:
    """Phase-4/5 entry point: structured requirement view for matching."""
    return service.get_job_requirements(job_id)


@router.get(
    "/{job_id}/raw-extraction",
    response_model=RawExtractionView,
    summary="Return the raw JSON produced by the extractor.",
)
async def get_raw_extraction(
    job_id: uuid.UUID,
    service: JobServiceDep,
) -> RawExtractionView:
    """Expose the extractor JSON verbatim for debugging and audits."""
    job = service.get_job(job_id)
    return RawExtractionView(payload=dict(job.raw_extraction or {}))


# ----------------------------------------------------------------------
# Embedding
# ----------------------------------------------------------------------
@router.post(
    "/{job_id}/embedding",
    response_model=EmbeddingRegenerateResponse,
    status_code=status.HTTP_200_OK,
    summary="(Re)generate the embedding vector for a job.",
)
async def regenerate_embedding(
    job_id: uuid.UUID,
    service: JobServiceDep,
) -> EmbeddingRegenerateResponse:
    """Regenerate and persist the vector embedding for an existing job."""
    embedding = service.generate_job_embedding(job_id)
    return EmbeddingRegenerateResponse(
        job_id=embedding.job_id,
        model_name=embedding.model_name,
        dimension=embedding.dimension,
        regenerated=True,
    )


@router.get(
    "/{job_id}/embedding",
    response_model=JobEmbeddingDetailRead,
    summary="Fetch the embedding vector for a job.",
)
async def get_embedding(
    job_id: uuid.UUID,
    service: JobServiceDep,
    include_vector: bool = Query(
        default=True,
        description="When False, the response omits the vector payload.",
    ),
) -> JobEmbeddingDetailRead:
    """Return the persisted embedding plus its metadata for FAISS indexing."""
    job = service.get_job(job_id)
    if job.embedding is None:
        # Build it on demand so the endpoint is idempotent.
        embedding = service.generate_job_embedding(job.id)
    else:
        embedding = job.embedding

    response = JobEmbeddingDetailRead.model_validate(embedding)
    if not include_vector:
        response = response.model_copy(update={"vector": []})
    return response


__all__ = ["router"]
