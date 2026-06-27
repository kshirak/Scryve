"""Structured explanations of why a candidate fits (or doesn't) a JD.

Sprint 2 ships the structural helpers: skill diffing, strength /
weakness summaries, and disqualifier detection. The actual scoring layer
will consume these in Sprint 4 to produce the human-readable
``reasoning`` column required by the hackathon submission spec.
"""

from __future__ import annotations

from datetime import date

from app.intelligence.domain import (
    Candidate,
    CandidateExplanation,
    CandidateFeatures,
    JobProfile,
)
from app.intelligence.preprocessors.text import normalize_text, tokenize


# ----------------------------------------------------------------------
# Skill matching
# ----------------------------------------------------------------------
def _candidate_skill_corpus(candidate: Candidate) -> str:
    """Build a single searchable string covering everything a candidate claims.

    Pulls from the skills list plus titles and descriptions in the
    experience history, so a candidate who *did* the work but didn't list
    the buzzword still matches.
    """
    parts: list[str] = [s.name for s in candidate.skills]
    parts.extend(
        item
        for entry in candidate.experience
        for item in (entry.title, entry.description)
        if item
    )
    parts.append(candidate.profile.current_title or "")
    parts.append(candidate.profile.headline or "")
    parts.append(candidate.profile.summary or "")
    return normalize_text(" ".join(parts))


def match_keywords(
    candidate: Candidate, keywords: list[str]
) -> tuple[list[str], list[str]]:
    """Return ``(matched, missing)`` for a keyword list against a candidate.

    Comparison is case-insensitive and substring-based across the full
    candidate corpus (skills, titles, descriptions). The keywords are not
    reordered; uniqueness is preserved by insertion order.

    Args:
        candidate: The candidate to inspect.
        keywords: Keywords to look for.

    Returns:
        A tuple of (matched_keywords, missing_keywords).
    """
    corpus = _candidate_skill_corpus(candidate)
    matched: list[str] = []
    missing: list[str] = []
    for keyword in keywords:
        kw = keyword.lower().strip()
        if not kw:
            continue
        if kw in corpus:
            matched.append(keyword)
        else:
            missing.append(keyword)
    return matched, missing


# ----------------------------------------------------------------------
# Disqualifiers
# ----------------------------------------------------------------------
def detect_disqualifiers(
    candidate: Candidate, job: JobProfile
) -> list[str]:
    """Return JD disqualifier keywords that appear in the candidate's profile.

    For the Redrob JD this catches things like 100% consulting-firm
    history (TCS / Infosys / ...).

    Args:
        candidate: The candidate.
        job: The job profile (with `disqualifier_keywords`).

    Returns:
        List of triggered disqualifier strings.
    """
    if not job.disqualifier_keywords:
        return []

    corpus_parts: list[str] = []
    corpus_parts.extend(e.company or "" for e in candidate.experience)
    corpus_parts.append(candidate.profile.current_company or "")
    corpus_parts.append(candidate.profile.summary or "")
    corpus = normalize_text(" ".join(corpus_parts))

    triggered: list[str] = []
    for keyword in job.disqualifier_keywords:
        if keyword.lower() in corpus:
            triggered.append(keyword)
    return triggered


# ----------------------------------------------------------------------
# Strengths / weaknesses
# ----------------------------------------------------------------------
_STRENGTH_THRESHOLDS = {
    "career_stability_score": 0.75,
    "company_progression_score": 0.7,
    "education_score": 0.8,
    "certification_score": 0.6,
    "behavioral_engagement_score": 0.7,
    "availability_score": 0.75,
}

_WEAKNESS_THRESHOLDS = {
    "career_stability_score": 0.35,
    "behavioral_engagement_score": 0.35,
    "availability_score": 0.4,
}


def summarize_strengths(features: CandidateFeatures) -> list[str]:
    """Return short human-readable strength bullets for a candidate.

    Args:
        features: Engineered features.

    Returns:
        List of strength descriptions.
    """
    strengths: list[str] = []
    if features.total_experience_years >= 5:
        strengths.append(
            f"{features.total_experience_years:.1f} years of total experience"
        )
    if features.skill_count >= 8:
        strengths.append(f"Broad skill coverage ({features.skill_count} skills)")
    if (
        features.average_skill_proficiency is not None
        and features.average_skill_proficiency >= 0.7
    ):
        strengths.append(
            f"High average skill proficiency "
            f"({features.average_skill_proficiency:.2f})"
        )

    for field, threshold in _STRENGTH_THRESHOLDS.items():
        value = getattr(features, field)
        if value is None or value < threshold:
            continue
        strengths.append(f"Strong {field.replace('_', ' ')} ({value:.2f})")
    return strengths


def summarize_weaknesses(
    features: CandidateFeatures, candidate: Candidate
) -> list[str]:
    """Return short human-readable weakness bullets for a candidate.

    Args:
        features: Engineered features.
        candidate: The candidate (used for raw signal context).

    Returns:
        List of weakness descriptions.
    """
    weaknesses: list[str] = []
    if features.total_experience_years < 2:
        weaknesses.append(
            f"Limited experience ({features.total_experience_years:.1f} yrs)"
        )
    if features.skill_count < 3:
        weaknesses.append(f"Sparse skill list ({features.skill_count} skills)")

    for field, threshold in _WEAKNESS_THRESHOLDS.items():
        value = getattr(features, field)
        if value is None or value > threshold:
            continue
        weaknesses.append(f"Low {field.replace('_', ' ')} ({value:.2f})")

    signals = candidate.signals
    if (
        signals.recruiter_response_rate is not None
        and signals.recruiter_response_rate < 0.2
    ):
        weaknesses.append(
            f"Low recruiter response rate "
            f"({signals.recruiter_response_rate:.0%})"
        )
    if signals.last_active_date is not None:
        days = (date.today() - signals.last_active_date).days
        if days > 90:
            weaknesses.append(f"Inactive for {days} days")
    if (
        signals.notice_period_days is not None
        and signals.notice_period_days > 60
    ):
        weaknesses.append(
            f"Long notice period ({signals.notice_period_days} days)"
        )
    return weaknesses


# ----------------------------------------------------------------------
# Headline + composite explanation
# ----------------------------------------------------------------------
def build_headline(candidate: Candidate, features: CandidateFeatures) -> str:
    """Return a one-line summary suitable for the ``reasoning`` column.

    Example:
        ``"Senior AI Engineer · 6.2 yrs · 9 skills · engagement 0.78"``

    Args:
        candidate: The candidate.
        features: Engineered features.

    Returns:
        One-line headline string.
    """
    title = (
        candidate.profile.current_title
        or candidate.profile.headline
        or "Candidate"
    )
    parts = [
        title,
        f"{features.total_experience_years:.1f} yrs",
        f"{features.skill_count} skills",
        f"engagement {features.behavioral_engagement_score:.2f}",
    ]
    return " · ".join(parts)


def explain(
    candidate: Candidate,
    job: JobProfile,
    features: CandidateFeatures,
) -> CandidateExplanation:
    """Build a `CandidateExplanation` aggregate for a candidate against a JD.

    Args:
        candidate: The candidate.
        job: Target job profile.
        features: Engineered features.

    Returns:
        A populated `CandidateExplanation`.
    """
    required_keywords = job.required_keywords or job.required_skills
    preferred_keywords = job.preferred_keywords or job.preferred_skills

    matched_req, missing_req = match_keywords(candidate, required_keywords)
    matched_pref, missing_pref = match_keywords(candidate, preferred_keywords)
    triggered = detect_disqualifiers(candidate, job)

    strengths = summarize_strengths(features)
    weaknesses = summarize_weaknesses(features, candidate)

    concerns: list[str] = []
    if missing_req:
        concerns.append(
            f"Missing {len(missing_req)} required signals: "
            f"{', '.join(missing_req[:3])}"
            + ("…" if len(missing_req) > 3 else "")
        )
    if triggered:
        concerns.append(
            "Profile contains JD disqualifier signal(s): "
            + ", ".join(triggered)
        )

    return CandidateExplanation(
        candidate_id=candidate.candidate_id,
        matched_required_skills=matched_req,
        missing_required_skills=missing_req,
        matched_preferred_skills=matched_pref,
        missing_preferred_skills=missing_pref,
        triggered_disqualifiers=triggered,
        strengths=strengths,
        weaknesses=weaknesses,
        concerns=concerns,
        headline=build_headline(candidate, features),
    )


# Silence unused-import linters: `tokenize` is exported for future skill
# tokenization tasks.
_ = tokenize
