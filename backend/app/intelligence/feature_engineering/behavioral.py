"""Behavioral-engagement features derived from `redrob_signals`.

The JD is explicit: a perfect-on-paper candidate who hasn't logged in for
months and ignores recruiters is, for hiring purposes, *not available*.
This module turns the 23 raw signals into a single engagement score that
the ranker can use as a multiplier (or as a feature in a learned ranker).
"""

from __future__ import annotations

from datetime import date

from app.intelligence.domain import Candidate

_RECENT_ACTIVITY_DAYS = 90  # 0..1 falloff from "today" to this window edge.


def _days_since(reference: date | None, today: date | None = None) -> float | None:
    """Days between `reference` and `today` (default: today). None-safe."""
    if reference is None:
        return None
    base = today or date.today()
    return max(0.0, (base - reference).days)


def _last_active_score(last_active: date | None) -> float:
    """Map last-active date to a [0, 1] recency score."""
    days = _days_since(last_active)
    if days is None:
        return 0.5  # missing → neutral
    if days >= _RECENT_ACTIVITY_DAYS:
        return 0.0
    return round(1.0 - days / _RECENT_ACTIVITY_DAYS, 4)


def _safe(value: float | None, default: float = 0.5) -> float:
    """Use `default` (neutral) when the signal is missing."""
    return default if value is None else max(0.0, min(1.0, value))


def behavioral_engagement_score(candidate: Candidate) -> float:
    """Composite [0, 1] engagement score.

    Components (weights sum to 1.0):

    * Recruiter response rate (35%)
    * Last-active recency (25%)
    * Interview completion rate (20%)
    * Profile completeness (10%)
    * Open-to-work flag (10%)

    Missing signals default to a neutral 0.5 so candidates with sparse
    profiles are neither rewarded nor punished, only de-prioritized
    relative to those with strong positive signals.

    Args:
        candidate: The candidate.

    Returns:
        Engagement score in [0, 1].
    """
    s = candidate.signals

    response = _safe(s.recruiter_response_rate)
    activity = _last_active_score(s.last_active_date)
    interview = _safe(s.interview_completion_rate)
    completeness = _safe(
        s.profile_completeness_score / 100.0
        if s.profile_completeness_score is not None
        else None
    )
    open_to_work = 1.0 if s.open_to_work_flag else (0.3 if s.open_to_work_flag is False else 0.5)

    score = (
        0.35 * response
        + 0.25 * activity
        + 0.20 * interview
        + 0.10 * completeness
        + 0.10 * open_to_work
    )
    return round(min(1.0, max(0.0, score)), 4)
