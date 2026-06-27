"""Relocation features.

The hackathon JD pins the role to Pune/Noida (with NCR/Hyderabad/Mumbai
acceptable). Without a target location at feature-engineering time we
expose two views: a candidate-only score (purely from the
``willing_to_relocate`` flag) and a location-match helper that takes a
JobProfile and returns a boolean.

Composite location matching is intentionally left to the ranking stage so
this module stays a pure function of the candidate.
"""

from __future__ import annotations

from app.intelligence.domain import Candidate, JobProfile
from app.intelligence.preprocessors.text import normalize_text


def relocation_score(candidate: Candidate) -> float:
    """[0, 1] willingness-to-relocate score.

    * `True`  → 1.0
    * `False` → 0.0
    * Missing → 0.5 (neutral)

    Args:
        candidate: The candidate.

    Returns:
        Relocation score in [0, 1].
    """
    flag = candidate.signals.willing_to_relocate
    if flag is True:
        return 1.0
    if flag is False:
        return 0.0
    return 0.5


def location_matches(candidate: Candidate, job: JobProfile) -> bool:
    """True when the candidate's location is in the JD's accepted set.

    Comparison is case-insensitive and substring-based so ``"Pune, India"``
    matches ``"Pune"`` in the JD location list.

    Args:
        candidate: The candidate.
        job: The job profile to compare against.

    Returns:
        True if the candidate's location matches one of the JD locations.
    """
    if not candidate.profile.location or not job.locations:
        return False
    location = normalize_text(candidate.profile.location)
    return any(normalize_text(loc) in location for loc in job.locations)
