"""Smoke test: load real hackathon data, validate, parse, compute features.

These tests are skipped automatically when the dataset files are not
present (e.g. CI without the data drop). When present, they assert that:

* Every sample candidate validates against the real `candidate_schema.json`.
* The parser maps every field (nested profile, career history, education
  tier, skills, signals) into a populated `Candidate`.
* The full feature pipeline produces sensible `CandidateFeatures`.
* Explainability runs end-to-end against the curated JD.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.intelligence.explainability import explain
from app.intelligence.feature_engineering import FeaturePipeline
from app.intelligence.loaders import CandidateLoader, load_job_profile_yaml
from app.intelligence.parsers.candidate_parser import CandidateParser

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SAMPLE = DATA_DIR / "sample_candidates.json"
SCHEMA = DATA_DIR / "candidate_schema.json"
JOB_PROFILE = DATA_DIR / "job_profiles" / "redrob_senior_ai_engineer.yaml"


pytestmark = pytest.mark.skipif(
    not SAMPLE.exists() or not SCHEMA.exists(),
    reason="Hackathon dataset not present; smoke tests skipped.",
)


@pytest.fixture(scope="module")
def sample_records() -> list[dict]:
    with SAMPLE.open("rt", encoding="utf-8") as handle:
        return json.load(handle)


@pytest.fixture(scope="module")
def jsonl_path(tmp_path_factory, sample_records) -> Path:
    """Materialize the sample JSON as JSONL so the loader can stream it."""
    path = tmp_path_factory.mktemp("smoke") / "sample.jsonl"
    with path.open("wt", encoding="utf-8") as handle:
        for record in sample_records:
            handle.write(json.dumps(record) + "\n")
    return path


def test_real_records_pass_schema_validation(jsonl_path, sample_records):
    loader = CandidateLoader(schema_path=SCHEMA)
    valid_count = loader.count(jsonl_path)
    assert valid_count == len(sample_records), (
        f"{len(sample_records) - valid_count} records failed schema validation"
    )


def test_parser_maps_nested_profile(sample_records):
    parser = CandidateParser()
    first = parser.parse(sample_records[0])

    # Nested profile should land on the Candidate.profile object.
    assert first.profile.name  # anonymized_name
    assert first.profile.current_title
    assert first.profile.current_company
    assert first.profile.current_company_size  # only present in real schema
    assert first.profile.current_industry
    assert first.profile.country
    assert first.profile.total_experience_years is not None


def test_parser_captures_schema_specific_fields(sample_records):
    parser = CandidateParser()
    candidate = parser.parse(sample_records[0])

    # career_history entries carry duration_months + industry + size.
    assert candidate.experience, "expected at least one experience entry"
    head = candidate.experience[0]
    assert head.duration_months is not None
    assert head.industry is not None
    assert head.company_size is not None
    # Duration in years comes from duration_months for accuracy.
    assert head.duration_years == round(head.duration_months / 12.0, 2)

    # Skills should carry endorsements + duration_months.
    assert candidate.skills
    first_skill = candidate.skills[0]
    assert first_skill.endorsements is not None
    assert first_skill.duration_months is not None

    # Education should carry tier + grade text.
    if candidate.education:
        edu = candidate.education[0]
        assert edu.tier in {"tier_1", "tier_2", "tier_3", "tier_4", "unknown", None}
        # `grade` is preserved as a string; `gpa` is numeric when extractable.
        if edu.grade and any(c.isdigit() for c in edu.grade):
            assert edu.gpa is not None


def test_full_pipeline_on_real_samples(sample_records):
    parser = CandidateParser()
    pipeline = FeaturePipeline()
    job = load_job_profile_yaml(JOB_PROFILE)

    for record in sample_records[:20]:
        candidate = parser.parse(record)
        features = pipeline.compute(candidate)
        explanation = explain(candidate, job, features)

        # Sanity: scores are in [0, 1].
        for field in (
            "career_stability_score",
            "company_progression_score",
            "education_score",
            "certification_score",
            "behavioral_engagement_score",
            "availability_score",
            "relocation_score",
        ):
            value = getattr(features, field)
            assert 0.0 <= value <= 1.0, (
                f"{field}={value} out of range for {candidate.candidate_id}"
            )

        # Explanation always returns a headline and disjoint keyword lists.
        assert explanation.headline
        overlap = set(explanation.matched_required_skills) & set(
            explanation.missing_required_skills
        )
        assert not overlap


def test_real_dataset_streaming_if_full_pool_present():
    """If the 100k pool is present, ensure the first few hundred records load."""
    full_jsonl = DATA_DIR / "candidates.jsonl"
    if not full_jsonl.exists():
        pytest.skip("Full 100k candidates.jsonl not present")

    loader = CandidateLoader(schema_path=SCHEMA)
    streamed = 0
    for candidate in loader.iter_candidates(full_jsonl):
        assert candidate.candidate_id.startswith("CAND_")
        streamed += 1
        if streamed >= 200:
            break
    assert streamed == 200
