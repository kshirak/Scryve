"""Certification-derived features."""

from __future__ import annotations

from datetime import date

from app.intelligence.domain import Candidate

# Saturating count: beyond this many certifications, additional ones don't
# meaningfully change the score.
_SATURATION = 5
_RECENCY_WINDOW_YEARS = 5


def certification_count(candidate: Candidate) -> int:
    """Number of certifications listed on the profile."""
    return len(candidate.certifications)


def certification_score(candidate: Candidate) -> float:
    """[0, 1] certification score combining count and recency.

    * Count contributes up to 0.6 (saturating at ``_SATURATION``).
    * Recency contributes up to 0.4, where 1.0 means at least one
      certification was issued within the last `_RECENCY_WINDOW_YEARS`.

    Args:
        candidate: The candidate.

    Returns:
        Certification score in [0, 1].
    """
    if not candidate.certifications:
        return 0.0

    count = len(candidate.certifications)
    count_component = min(1.0, count / _SATURATION) * 0.6

    today = date.today()
    recency_component = 0.0
    for cert in candidate.certifications:
        if cert.issued_year is None:
            continue
        age = today.year - cert.issued_year
        if 0 <= age <= _RECENCY_WINDOW_YEARS:
            recency_component = max(
                recency_component,
                1.0 - (age / _RECENCY_WINDOW_YEARS),
            )
    recency_component *= 0.4

    return round(count_component + recency_component, 4)
