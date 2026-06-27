"""Skill-derived features."""

from __future__ import annotations

from typing import Any

from app.intelligence.domain import Candidate

# Coarse mapping of common proficiency words to a [0, 1] scale.
_PROFICIENCY_WORDS: dict[str, float] = {
    "novice": 0.2,
    "beginner": 0.25,
    "basic": 0.3,
    "intermediate": 0.5,
    "proficient": 0.6,
    "advanced": 0.75,
    "expert": 1.0,
    "master": 1.0,
}


def _coerce_proficiency(value: Any) -> float | None:
    """Map a proficiency value to a [0, 1] float, or None if unknown.

    Accepts numeric values (assumed 0..100 when > 1, else 0..1) and a few
    common qualitative words.

    Args:
        value: Raw proficiency value.

    Returns:
        Normalized proficiency in [0, 1] or `None`.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        numeric = float(value)
        if numeric < 0:
            return None
        return min(1.0, numeric / 100.0 if numeric > 1 else numeric)
    if isinstance(value, str):
        return _PROFICIENCY_WORDS.get(value.strip().lower())
    return None


def skill_count(candidate: Candidate) -> int:
    """Number of skills listed on the candidate's profile."""
    return len(candidate.skills)


def average_skill_proficiency(candidate: Candidate) -> float | None:
    """Average proficiency across skills with a numeric / known level.

    Args:
        candidate: The candidate.

    Returns:
        Mean proficiency in [0, 1], or `None` if no skills have a
        recognizable proficiency value.
    """
    levels: list[float] = []
    for skill in candidate.skills:
        coerced = _coerce_proficiency(skill.proficiency)
        if coerced is not None:
            levels.append(coerced)
    if not levels:
        return None
    return round(sum(levels) / len(levels), 4)
