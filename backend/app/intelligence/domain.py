"""Internal domain models for the intelligence layer.

These objects are the contract between parsers, analyzers, feature
engineering, and downstream ranking/explainability modules. They are
deliberately decoupled from any HTTP request/response schema in
`app.schemas` because they describe internal computation state, not API
payloads.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


# ----------------------------------------------------------------------
# Candidate sub-models
# ----------------------------------------------------------------------
class Skill(BaseModel):
    """A single self-declared or platform-derived skill."""

    name: str
    proficiency: Optional[str | float] = None
    years_used: Optional[float] = None
    last_used_year: Optional[int] = None
    duration_months: Optional[int] = None
    endorsements: Optional[int] = None


class ExperienceEntry(BaseModel):
    """One job/employment row from the candidate's career history."""

    company: Optional[str] = None
    title: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    is_current: bool = False
    description: Optional[str] = None
    location: Optional[str] = None
    duration_years: Optional[float] = None
    duration_months: Optional[int] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None


class EducationEntry(BaseModel):
    """One academic degree row.

    `grade` is kept as a free-form string ("8.24 CGPA", "First Class")
    because real datasets ship a mix of formats. `gpa` is the numeric
    component extracted from `grade` when possible.
    """

    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    grade: Optional[str] = None
    gpa: Optional[float] = None
    tier: Optional[str] = None


class CertificationEntry(BaseModel):
    """A professional certification."""

    name: str
    issuer: Optional[str] = None
    issued_year: Optional[int] = None
    expires_year: Optional[int] = None


class LanguageEntry(BaseModel):
    """A spoken/written language and proficiency."""

    name: str
    proficiency: Optional[str] = None


class BehavioralSignals(BaseModel):
    """All 23 Redrob behavioral signals.

    Field names mirror the public signal documentation so downstream code
    can refer to them by the same names that ground-truth and recruiter
    teams use.
    """

    profile_completeness_score: Optional[float] = None
    signup_date: Optional[date] = None
    last_active_date: Optional[date] = None
    open_to_work_flag: Optional[bool] = None
    profile_views_received_30d: Optional[int] = None
    applications_submitted_30d: Optional[int] = None
    recruiter_response_rate: Optional[float] = None
    avg_response_time_hours: Optional[float] = None
    skill_assessment_scores: dict[str, float] = Field(default_factory=dict)
    connection_count: Optional[int] = None
    endorsements_received: Optional[int] = None
    notice_period_days: Optional[int] = None
    expected_salary_min_lpa: Optional[float] = None
    expected_salary_max_lpa: Optional[float] = None
    preferred_work_mode: Optional[str] = None
    willing_to_relocate: Optional[bool] = None
    github_activity_score: Optional[float] = None
    search_appearance_30d: Optional[int] = None
    saved_by_recruiters_30d: Optional[int] = None
    interview_completion_rate: Optional[float] = None
    offer_acceptance_rate: Optional[float] = None
    verified_email: Optional[bool] = None
    verified_phone: Optional[bool] = None
    linkedin_connected: Optional[bool] = None


class CandidateProfile(BaseModel):
    """Top-level identity / summary fields for a candidate."""

    candidate_id: str
    name: Optional[str] = None
    headline: Optional[str] = None
    current_title: Optional[str] = None
    current_company: Optional[str] = None
    current_company_size: Optional[str] = None
    current_industry: Optional[str] = None
    location: Optional[str] = None
    country: Optional[str] = None
    total_experience_years: Optional[float] = None
    summary: Optional[str] = None
    email: Optional[str] = None


# ----------------------------------------------------------------------
# Candidate aggregate
# ----------------------------------------------------------------------
class Candidate(BaseModel):
    """The intelligence-layer representation of one candidate.

    `raw` retains the original record so downstream debugging and
    fall-through parsing remain possible without re-reading the file.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    candidate_id: str
    profile: CandidateProfile
    experience: list[ExperienceEntry] = Field(default_factory=list)
    education: list[EducationEntry] = Field(default_factory=list)
    skills: list[Skill] = Field(default_factory=list)
    certifications: list[CertificationEntry] = Field(default_factory=list)
    languages: list[LanguageEntry] = Field(default_factory=list)
    signals: BehavioralSignals = Field(default_factory=BehavioralSignals)
    raw: dict[str, Any] = Field(default_factory=dict, repr=False, exclude=True)


# ----------------------------------------------------------------------
# Job profile
# ----------------------------------------------------------------------
class JobProfile(BaseModel):
    """Structured representation of a job description.

    Bullet items are stored as full requirement strings rather than parsed
    skill tokens; the keyword lists below provide a parallel, denormalized
    view for matching layers (BM25, embedding seeds, etc.).
    """

    role_title: str
    industry: Optional[str] = None
    experience_min_years: Optional[float] = None
    experience_max_years: Optional[float] = None
    locations: list[str] = Field(default_factory=list)

    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    mandatory_requirements: list[str] = Field(default_factory=list)
    nice_to_have_requirements: list[str] = Field(default_factory=list)
    disqualifiers: list[str] = Field(default_factory=list)

    required_keywords: list[str] = Field(default_factory=list)
    preferred_keywords: list[str] = Field(default_factory=list)
    disqualifier_keywords: list[str] = Field(default_factory=list)

    behavioral_thresholds: dict[str, float] = Field(default_factory=dict)
    raw_text: Optional[str] = Field(default=None, repr=False, exclude=True)


# ----------------------------------------------------------------------
# Feature output
# ----------------------------------------------------------------------
class CandidateFeatures(BaseModel):
    """Reusable, normalized features derived from a `Candidate`.

    All scalar scores are normalized to roughly the `[0, 1]` range so
    downstream rankers can combine them linearly without re-scaling.
    Raw values (e.g. total experience in years) are exposed alongside the
    normalized scores for transparency.
    """

    candidate_id: str

    # Raw quantities
    total_experience_years: float = 0.0
    skill_count: int = 0
    average_skill_proficiency: Optional[float] = None
    average_tenure_years: Optional[float] = None
    job_count: int = 0
    certification_count: int = 0
    education_levels: list[str] = Field(default_factory=list)

    # Normalized 0..1 scores
    career_stability_score: float = 0.0
    company_progression_score: float = 0.0
    education_score: float = 0.0
    certification_score: float = 0.0
    behavioral_engagement_score: float = 0.0
    availability_score: float = 0.0
    relocation_score: float = 0.0


# ----------------------------------------------------------------------
# Explainability output
# ----------------------------------------------------------------------
class CandidateExplanation(BaseModel):
    """Structured explanation of how a candidate stacks up against a JD."""

    candidate_id: str
    matched_required_skills: list[str] = Field(default_factory=list)
    missing_required_skills: list[str] = Field(default_factory=list)
    matched_preferred_skills: list[str] = Field(default_factory=list)
    missing_preferred_skills: list[str] = Field(default_factory=list)
    triggered_disqualifiers: list[str] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    headline: Optional[str] = None
