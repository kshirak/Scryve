"""Education-derived features."""

from __future__ import annotations

from app.intelligence.domain import Candidate, EducationEntry

# Coarse tier mapping. Order matters for matching: higher tiers are checked
# first so "Master of Engineering" doesn't match "Bachelor".
_DEGREE_TIERS: list[tuple[float, tuple[str, ...]]] = [
    (1.0, ("phd", "doctorate", "d.phil", "dphil")),
    (0.85, ("mba", "executive mba")),
    (0.8, ("master", "m.tech", "m.sc", "ms ", "msc", "ma ", "m.a")),
    (0.6, ("bachelor", "b.tech", "b.sc", "bs ", "bsc", "ba ", "b.a", "be ", "b.e")),
    (0.4, ("diploma", "associate")),
    (0.3, ("high school", "secondary")),
]

# Institution tier mapping (matches the `tier` enum in the Redrob schema).
_INSTITUTION_TIER_WEIGHTS: dict[str, float] = {
    "tier_1": 1.0,
    "tier_2": 0.75,
    "tier_3": 0.5,
    "tier_4": 0.3,
    "unknown": 0.5,
}


def _degree_tier(degree: str | None) -> float:
    """Map a free-text degree string to a tier weight in [0, 1]."""
    if not degree:
        return 0.0
    lowered = degree.lower()
    for weight, keywords in _DEGREE_TIERS:
        if any(keyword in lowered for keyword in keywords):
            return weight
    return 0.0


def _institution_tier(entry: EducationEntry) -> float | None:
    """Return the institution tier weight, or None when not provided."""
    if not entry.tier:
        return None
    return _INSTITUTION_TIER_WEIGHTS.get(entry.tier.lower())


def education_score(candidate: Candidate) -> float:
    """Aggregate [0, 1] education score.

    Strategy:
        * Take the highest single degree tier achieved.
        * Blend with institution tier (60% degree, 40% institution) when
          a tier label is present on the strongest degree's entry.
        * Add a small bonus for each additional degree at tier >= 0.4.
        * Clip at 1.0.

    Returns:
        Education score in [0, 1].
    """
    if not candidate.education:
        return 0.0

    scored = [(_degree_tier(e.degree), _institution_tier(e), e) for e in candidate.education]
    scored.sort(key=lambda item: item[0], reverse=True)

    primary_degree, primary_inst_tier, _ = scored[0]
    if primary_inst_tier is not None:
        primary = 0.6 * primary_degree + 0.4 * primary_inst_tier
    else:
        primary = primary_degree

    extras = sum(1 for d, _, _ in scored if d >= 0.4) - 1
    return round(min(1.0, primary + max(0, extras) * 0.05), 4)


def education_labels(candidate: Candidate) -> list[str]:
    """Return a stable list of degree labels, e.g. ``['Master', 'Bachelor']``."""
    labels: list[str] = []
    for entry in candidate.education:
        label = _label_for(entry)
        if label and label not in labels:
            labels.append(label)
    return labels


def _label_for(entry: EducationEntry) -> str | None:
    """Map a single education entry to a coarse label."""
    if not entry.degree:
        return None
    lowered = entry.degree.lower()
    for weight, keywords in _DEGREE_TIERS:
        if any(keyword in lowered for keyword in keywords):
            return {
                1.0: "PhD",
                0.85: "MBA",
                0.8: "Master",
                0.6: "Bachelor",
                0.4: "Diploma",
                0.3: "High School",
            }.get(weight)
    return entry.degree.strip().title() or None
