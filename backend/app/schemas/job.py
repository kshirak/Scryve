"""Request / response schemas for the Job Intelligence API.

These schemas are the contract between the HTTP layer and the rest of
the application. They are deliberately decoupled from the
:class:`app.intelligence.parsers.job_extractor.JobExtraction` domain
record — the API can change shape without disturbing the extractor, and
vice versa.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ORMModel


# ----------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------
class JobCreate(BaseModel):
    """Payload accepted when creating a job description."""

    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description=(
            "Optional human-curated title. When omitted, the extractor will "
            "infer a role title from the JD text."
        ),
    )
    description: str = Field(
        ...,
        min_length=20,
        description="Raw JD text. Markdown is preferred but plain text works.",
    )
    source_format: str = Field(
        default="text",
        description="Origin of the JD body ('text', 'markdown', 'docx', 'yaml').",
        max_length=20,
    )
    generate_embedding: bool = Field(
        default=True,
        description="When True, generate and persist the embedding inline.",
    )


# ----------------------------------------------------------------------
# Extraction view (no DB persistence)
# ----------------------------------------------------------------------
class JobExtractionResponse(BaseModel):
    """The output of an extraction-only call (no DB write)."""

    title: Optional[str] = None
    role: Optional[str] = None
    industry: Optional[str] = None
    experience_level: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    locations: list[str] = Field(default_factory=list)

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    tools_frameworks: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)

    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    extracted_keywords: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------
# Persisted views
# ----------------------------------------------------------------------
class JobEmbeddingRead(ORMModel):
    """Read view of a job embedding (without the heavy vector by default)."""

    id: uuid.UUID
    job_id: uuid.UUID
    model_name: str
    dimension: int
    created_at: datetime
    updated_at: datetime


class JobEmbeddingDetailRead(JobEmbeddingRead):
    """Detail view that includes the raw vector."""

    vector: list[float] = Field(
        default_factory=list,
        description="L2-normalized vector ready for FAISS IndexFlatIP.",
    )


class JobRead(ORMModel):
    """Default read view: all extracted fields, embedding metadata only."""

    id: uuid.UUID
    title: str
    description: str
    role: Optional[str] = None
    industry: Optional[str] = None
    experience_level: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    locations: list[str] = Field(default_factory=list)

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    tools_frameworks: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)

    responsibilities: list[str] = Field(default_factory=list)
    qualifications: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    extracted_keywords: list[str] = Field(default_factory=list)

    source_format: str = "text"
    created_at: datetime
    updated_at: datetime

    embedding: Optional[JobEmbeddingRead] = None


class JobListItem(ORMModel):
    """Compact list view returned by ``GET /jobs``."""

    id: uuid.UUID
    title: str
    role: Optional[str] = None
    experience_level: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    required_skills: list[str] = Field(default_factory=list)
    created_at: datetime


class JobRequirements(BaseModel):
    """The matching-ready view a Phase-4 ranker consumes.

    Returned by :func:`JobService.get_job_requirements` and the
    ``GET /jobs/{id}/requirements`` endpoint. Kept minimal so consumers
    are not coupled to the full record shape.
    """

    model_config = ConfigDict(from_attributes=True)

    job_id: uuid.UUID
    title: str
    role: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    experience_level: Optional[str] = None
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    soft_skills: list[str] = Field(default_factory=list)
    programming_languages: list[str] = Field(default_factory=list)
    tools_frameworks: list[str] = Field(default_factory=list)
    domain_knowledge: list[str] = Field(default_factory=list)
    education_requirements: list[str] = Field(default_factory=list)
    extracted_keywords: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)


# ----------------------------------------------------------------------
# Generic envelopes
# ----------------------------------------------------------------------
class EmbeddingRegenerateResponse(BaseModel):
    """Returned by the embedding regeneration endpoint."""

    job_id: uuid.UUID
    model_name: str
    dimension: int
    regenerated: bool = True


class RawExtractionView(BaseModel):
    """Wraps the raw extractor JSON for clients that want it verbatim."""

    payload: dict[str, Any] = Field(default_factory=dict)
