"""Career-trajectory analyses.

These helpers turn a candidate's `ExperienceEntry` list into structural
signals: how stable the candidate has been across jobs and whether their
title progression suggests upward mobility. All scores are in [0, 1].
"""

from __future__ import annotations

import statistics
from typing import Sequence

from app.intelligence.domain import ExperienceEntry
from app.intelligence.preprocessors.dates import duration_years

# Seniority lexicon used as a coarse heuristic. The exact rank value is
# less important than the *ordering* between levels.
_SENIORITY_LEVELS: list[tuple[int, tuple[str, ...]]] = [
    (1, ("intern", "trainee", "apprentice")),
    (2, ("junior", "associate", "jr")),
    (3, ("engineer", "analyst", "developer", "specialist", "consultant", "executive")),
    (4, ("senior", "sr", "sde 2", "ii", "level 2")),
    (5, ("staff", "lead", "principal", "tech lead", "team lead")),
    (6, ("manager", "head", "director")),
    (7, ("vp", "vice president", "chief", "cto", "ceo", "founder", "co-founder")),
]


def tenures_in_years(experience: Sequence[ExperienceEntry]) -> list[float]:
    """Return the tenure (in years) for every entry that has dates.

    Args:
        experience: Candidate experience list.

    Returns:
        List of tenure durations; entries without dates are skipped.
    """
    tenures: list[float] = []
    for entry in experience:
        if entry.duration_years is not None:
            tenures.append(entry.duration_years)
            continue
        computed = duration_years(entry.start_date, entry.end_date)
        if computed is not None:
            tenures.append(computed)
    return tenures


def average_tenure(experience: Sequence[ExperienceEntry]) -> float | None:
    """Return the average tenure across the candidate's jobs, in years.

    Args:
        experience: Candidate experience list.

    Returns:
        Mean tenure or `None` when no datable entries exist.
    """
    tenures = tenures_in_years(experience)
    if not tenures:
        return None
    return round(sum(tenures) / len(tenures), 2)


def career_stability_score(experience: Sequence[ExperienceEntry]) -> float:
    """Compute a [0, 1] stability score.

    Heuristic:
        * Average tenure in [2.0, 4.0] years is the sweet spot (score 1.0).
        * Tenure of 0 or below 1.0 (job-hopping) drives the score toward 0.
        * Very long average tenure (>6 yrs) is mildly penalized because the
          JD explicitly disfavors title-chasing as well as candidates who
          haven't shipped recently.
        * Standard deviation of tenures penalizes erratic histories.

    Args:
        experience: Candidate experience list.

    Returns:
        Stability score in [0, 1]. Returns 0.5 when no signal is available.
    """
    tenures = tenures_in_years(experience)
    if not tenures:
        return 0.5

    mean = sum(tenures) / len(tenures)
    if mean <= 0:
        return 0.0

    if 2.0 <= mean <= 4.0:
        mean_score = 1.0
    elif mean < 2.0:
        mean_score = max(0.0, mean / 2.0)
    else:  # mean > 4.0
        mean_score = max(0.3, 1.0 - (mean - 4.0) * 0.1)

    if len(tenures) >= 2:
        stdev = statistics.pstdev(tenures)
        variability_penalty = min(0.3, stdev / 5.0)
    else:
        variability_penalty = 0.0

    return round(max(0.0, min(1.0, mean_score - variability_penalty)), 4)


def _title_rank(title: str | None) -> int:
    """Map a job title to a coarse seniority rank (1-7)."""
    if not title:
        return 0
    normalized = title.lower()
    best = 0
    for rank, keywords in _SENIORITY_LEVELS:
        if any(keyword in normalized for keyword in keywords):
            best = max(best, rank)
    return best


def company_progression_score(experience: Sequence[ExperienceEntry]) -> float:
    """Score upward title progression across the career, in [0, 1].

    Ordering: from earliest job to latest. Each step that goes "up" in the
    seniority lexicon contributes positively; steps "down" are penalized.

    Args:
        experience: Candidate experience list.

    Returns:
        Progression score in [0, 1]. Returns 0.5 when fewer than two
        rankable jobs exist.
    """
    ordered = sorted(
        (e for e in experience if e.start_date is not None),
        key=lambda e: e.start_date,  # type: ignore[arg-type, return-value]
    )
    if len(ordered) < 2:
        # Fall back to raw order if no dates available.
        ordered = list(experience)

    ranks = [_title_rank(e.title) for e in ordered if _title_rank(e.title) > 0]
    if len(ranks) < 2:
        return 0.5

    transitions = len(ranks) - 1
    ups = sum(1 for i in range(transitions) if ranks[i + 1] > ranks[i])
    downs = sum(1 for i in range(transitions) if ranks[i + 1] < ranks[i])

    net = (ups - downs) / transitions
    return round((net + 1) / 2, 4)
