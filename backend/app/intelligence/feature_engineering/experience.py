"""Experience and career-progression features."""

from __future__ import annotations

from app.intelligence.analyzers.career import (
    average_tenure,
    career_stability_score,
    company_progression_score,
    tenures_in_years,
)
from app.intelligence.domain import Candidate


def total_experience_years(candidate: Candidate) -> float:
    """Return the candidate's total experience in years.

    Prefers the explicit `profile.total_experience_years` field; if absent,
    sums tenures derived from the experience list. Returns 0.0 when no
    information is available.

    Args:
        candidate: The candidate.

    Returns:
        Years of experience (>= 0).
    """
    if candidate.profile.total_experience_years is not None:
        return max(0.0, candidate.profile.total_experience_years)
    tenures = tenures_in_years(candidate.experience)
    return round(sum(tenures), 2) if tenures else 0.0


def job_count(candidate: Candidate) -> int:
    """Number of job entries the candidate has listed."""
    return len(candidate.experience)


def avg_tenure_years(candidate: Candidate) -> float | None:
    """Average tenure across listed jobs, or None when undeterminable."""
    return average_tenure(candidate.experience)


def career_stability(candidate: Candidate) -> float:
    """Normalized [0, 1] career-stability score."""
    return career_stability_score(candidate.experience)


def company_progression(candidate: Candidate) -> float:
    """Normalized [0, 1] upward-progression score."""
    return company_progression_score(candidate.experience)
