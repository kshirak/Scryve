"""Tests for the JD parser and curated YAML loader."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

from app.intelligence.loaders.jd_loader import load_job_profile_yaml
from app.intelligence.parsers.jd_parser import parse_job_description


def test_parses_required_and_preferred_bullets():
    text = dedent(
        """
        # Job Description: Senior AI Engineer

        Location: Pune, Noida

        Experience Required: 5-9 years

        ## Things you absolutely need

        - Python production experience
        - Vector search systems

        ## Things we'd like you to have

        - LoRA fine-tuning
        - Open-source contributions

        ## Things we explicitly do NOT want

        - Pure research-only background
        - Consulting-only career
        """
    ).strip()

    profile = parse_job_description(text)

    assert "Senior AI Engineer" in profile.role_title
    assert profile.experience_min_years == 5
    assert profile.experience_max_years == 9
    assert "Pune" in profile.locations
    assert "Python production experience" in profile.required_skills
    assert "LoRA fine-tuning" in profile.preferred_skills
    assert any("research" in d.lower() for d in profile.disqualifiers)


def test_loads_curated_yaml_profile():
    yaml_path = (
        Path(__file__).resolve().parents[2]
        / "data"
        / "job_profiles"
        / "redrob_senior_ai_engineer.yaml"
    )
    profile = load_job_profile_yaml(yaml_path)

    assert profile.role_title == "Senior AI Engineer"
    assert profile.experience_min_years == 5
    assert profile.experience_max_years == 9
    assert "Pune" in profile.locations
    assert "ndcg" in profile.required_keywords
    assert "tcs" in profile.disqualifier_keywords
