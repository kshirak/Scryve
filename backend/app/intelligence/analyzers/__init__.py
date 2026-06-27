"""Higher-order analyses computed from `Candidate` objects."""

from app.intelligence.analyzers.career import (
    average_tenure,
    career_stability_score,
    company_progression_score,
    tenures_in_years,
)

__all__ = [
    "average_tenure",
    "career_stability_score",
    "company_progression_score",
    "tenures_in_years",
]
