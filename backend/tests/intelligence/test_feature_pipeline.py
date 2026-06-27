"""Tests for the feature-engineering pipeline."""

from __future__ import annotations

from app.intelligence.feature_engineering import FeaturePipeline
from app.intelligence.parsers.candidate_parser import CandidateParser


def test_strong_candidate_produces_high_scores(sample_record):
    candidate = CandidateParser().parse(sample_record)
    features = FeaturePipeline().compute(candidate)

    assert features.total_experience_years == 6.5
    assert features.skill_count >= 4
    assert features.average_skill_proficiency is not None
    assert 0.7 <= features.average_skill_proficiency <= 1.0

    # Engagement signals are all positive in the strong profile.
    assert features.behavioral_engagement_score >= 0.7
    assert features.availability_score >= 0.7
    assert features.relocation_score == 1.0
    assert features.education_score >= 0.8  # Master + Bachelor


def test_weak_candidate_produces_low_scores(weak_record):
    candidate = CandidateParser().parse(weak_record)
    features = FeaturePipeline().compute(candidate)

    assert features.behavioral_engagement_score < 0.4
    assert features.availability_score <= 0.5
    assert features.relocation_score == 0.0


def test_pipeline_streams_features(sample_record, weak_record):
    candidates = [
        CandidateParser().parse(sample_record),
        CandidateParser().parse(weak_record),
    ]
    features = list(FeaturePipeline().compute_many(candidates))
    assert len(features) == 2
    assert features[0].behavioral_engagement_score > features[1].behavioral_engagement_score
