"""Feature-engineering pipeline orchestrator.

The pipeline owns one responsibility: turn a `Candidate` into a
`CandidateFeatures` aggregate by invoking the per-feature modules in a
deterministic order.

Ranking is deliberately *not* done here — the pipeline only produces
features. Downstream rankers (Sprint 4) consume `CandidateFeatures`.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from app.intelligence.domain import Candidate, CandidateFeatures
from app.intelligence.feature_engineering import (
    availability,
    behavioral,
    certifications,
    education,
    experience,
    relocation,
    skills,
)


class FeaturePipeline:
    """Composable feature pipeline.

    The pipeline is intentionally tiny: it has no internal state and no
    configuration. If we later want weighted features or feature toggles,
    they belong in the ranking layer, not here.
    """

    def compute(self, candidate: Candidate) -> CandidateFeatures:
        """Compute all features for a single candidate.

        Args:
            candidate: The candidate to engineer features for.

        Returns:
            A populated `CandidateFeatures` aggregate.
        """
        return CandidateFeatures(
            candidate_id=candidate.candidate_id,
            total_experience_years=experience.total_experience_years(candidate),
            skill_count=skills.skill_count(candidate),
            average_skill_proficiency=skills.average_skill_proficiency(candidate),
            average_tenure_years=experience.avg_tenure_years(candidate),
            job_count=experience.job_count(candidate),
            certification_count=certifications.certification_count(candidate),
            education_levels=education.education_labels(candidate),
            career_stability_score=experience.career_stability(candidate),
            company_progression_score=experience.company_progression(candidate),
            education_score=education.education_score(candidate),
            certification_score=certifications.certification_score(candidate),
            behavioral_engagement_score=behavioral.behavioral_engagement_score(
                candidate
            ),
            availability_score=availability.availability_score(candidate),
            relocation_score=relocation.relocation_score(candidate),
        )

    def compute_many(
        self, candidates: Iterable[Candidate]
    ) -> Iterator[CandidateFeatures]:
        """Stream-compute features for an iterable of candidates.

        Designed to compose with `CandidateLoader.iter_candidates` so the
        full 100k pool can be processed without materializing intermediate
        lists.

        Args:
            candidates: Iterable of `Candidate` objects.

        Yields:
            `CandidateFeatures` objects, one per candidate.
        """
        for candidate in candidates:
            yield self.compute(candidate)
