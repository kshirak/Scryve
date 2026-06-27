"""Tests for the explainability helpers."""

from __future__ import annotations

from pathlib import Path

from app.intelligence.explainability import explain
from app.intelligence.feature_engineering import FeaturePipeline
from app.intelligence.loaders.jd_loader import load_job_profile_yaml
from app.intelligence.parsers.candidate_parser import CandidateParser


def _load_job_profile():
    yaml_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "job_profiles"
        / "redrob_senior_ai_engineer.yaml"
    )
    return load_job_profile_yaml(yaml_path)


def test_strong_candidate_matches_required_keywords(sample_record):
    candidate = CandidateParser().parse(sample_record)
    features = FeaturePipeline().compute(candidate)
    job = _load_job_profile()

    explanation = explain(candidate, job, features)

    assert "faiss" in explanation.matched_required_skills or "FAISS" in explanation.matched_required_skills
    assert "python" in explanation.matched_required_skills or "Python" in explanation.matched_required_skills
    assert explanation.headline is not None
    assert len(explanation.strengths) >= 1


def test_weak_candidate_triggers_concerns(weak_record):
    candidate = CandidateParser().parse(weak_record)
    features = FeaturePipeline().compute(candidate)
    job = _load_job_profile()

    explanation = explain(candidate, job, features)

    # Title says Marketing Manager but skills are stuffed with AI keywords.
    # Behavioral signals are weak. Expect a non-empty weaknesses list.
    assert len(explanation.weaknesses) >= 1
    # Long missing-required list because the candidate is the wrong role.
    assert len(explanation.missing_required_skills) >= 5
