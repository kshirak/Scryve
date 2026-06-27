"""Unit tests for the candidate parser."""

from __future__ import annotations

import pytest

from app.intelligence.parsers.candidate_parser import CandidateParser


def test_parses_profile_and_skills(sample_record):
    candidate = CandidateParser().parse(sample_record)

    assert candidate.candidate_id == "CAND_0001234"
    assert candidate.profile.current_title.startswith("Senior")
    assert candidate.profile.location == "Pune, India"
    assert candidate.profile.total_experience_years == 6.5

    skill_names = [s.name for s in candidate.skills]
    assert "Python" in skill_names
    assert "Elasticsearch" in skill_names  # bare string skill is normalized


def test_parses_experience_with_dates(sample_record):
    candidate = CandidateParser().parse(sample_record)

    current = candidate.experience[0]
    assert current.is_current is True
    assert current.end_date is None
    assert current.start_date.year == 2022

    second = candidate.experience[1]
    assert second.duration_years is not None
    assert 2.5 <= second.duration_years <= 3.0


def test_parses_signals(sample_record):
    candidate = CandidateParser().parse(sample_record)
    s = candidate.signals

    assert s.recruiter_response_rate == 0.78
    assert s.willing_to_relocate is True
    assert s.expected_salary_min_lpa == 35
    assert s.expected_salary_max_lpa == 55
    assert s.skill_assessment_scores["Python"] == 92.0


def test_missing_candidate_id_raises(sample_record):
    sample_record.pop("candidate_id")
    with pytest.raises(ValueError):
        CandidateParser().parse(sample_record)


def test_backfills_total_experience_when_missing(sample_record):
    sample_record.pop("total_experience_years")
    candidate = CandidateParser().parse(sample_record)
    assert candidate.profile.total_experience_years is not None
    assert candidate.profile.total_experience_years > 7  # 3 jobs summed
