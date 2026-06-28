"""Tests for the Phase-3 job extractor."""

from __future__ import annotations

from textwrap import dedent

import pytest

from app.intelligence.parsers.job_extractor import JobExtractor, extract_job_intelligence


@pytest.fixture
def python_django_jd() -> str:
    return dedent(
        """
        # Backend Developer — Python / Django

        **Location:** Bangalore, Remote

        **Experience Required:** 2-4 years

        ## What you'll do

        - Build and maintain Django services that power our customer-facing APIs
        - Design REST APIs and document them
        - Optimize PostgreSQL queries
        - Mentor junior engineers

        ## Things you absolutely need

        - Strong Python production experience
        - Django and REST API design
        - PostgreSQL — query tuning, indexing
        - Git workflows and CI/CD

        ## Things we'd like you to have

        - Experience with Celery and Redis
        - Docker and Kubernetes
        - Familiarity with AWS

        ## Qualifications

        - Bachelor's degree in Computer Science
        - 2-4 years of professional backend engineering experience

        ## Things we explicitly do NOT want

        - Frontend-only profiles with no backend production exposure
        """
    ).strip()


def test_extracts_required_skills_with_normalization(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    assert "Python" in extraction.required_skills
    assert "Django" in extraction.required_skills
    assert "PostgreSQL" in extraction.required_skills
    assert "REST API" in extraction.required_skills


def test_categorizes_languages_and_frameworks(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    assert "Python" in extraction.programming_languages
    assert "Django" in extraction.tools_frameworks
    assert "PostgreSQL" in extraction.tools_frameworks  # database bucket


def test_preferred_skills_are_distinct_from_required(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    overlap = set(s.lower() for s in extraction.required_skills) & set(
        s.lower() for s in extraction.preferred_skills
    )
    assert overlap == set()

    assert "Kubernetes" in extraction.preferred_skills
    assert "Docker" in extraction.preferred_skills


def test_experience_range_and_level(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    assert extraction.experience_min_years == 2
    assert extraction.experience_max_years == 4
    assert extraction.experience_level == "Mid"


def test_responsibilities_pulled_from_section(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    assert any("Django" in r for r in extraction.responsibilities)
    assert any("REST" in r for r in extraction.responsibilities)


def test_education_requirements_detected(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    education_text = " ".join(extraction.education_requirements).lower()
    assert "bachelor" in education_text or "computer science" in education_text


def test_soft_skills_detected(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    assert "Leadership" in extraction.soft_skills  # mentoring junior engineers


def test_disqualifiers_extracted(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    assert any("frontend" in d.lower() for d in extraction.disqualifiers)


def test_extracted_keywords_are_lowercased(python_django_jd: str) -> None:
    extraction = extract_job_intelligence(python_django_jd)

    assert all(kw == kw.lower() for kw in extraction.extracted_keywords)
    assert "python" in extraction.extracted_keywords
    assert "postgresql" in extraction.extracted_keywords


def test_short_jd_round_trip_example_from_spec() -> None:
    text = (
        "Looking for Python Django developer with PostgreSQL experience "
        "and REST API knowledge. 2-4 years experience required."
    )
    extraction = extract_job_intelligence(text, title="Backend Developer")

    expected = {"Python", "Django", "PostgreSQL", "REST API"}
    assert expected.issubset(set(extraction.required_skills))
    assert extraction.title == "Backend Developer"
    assert extraction.experience_min_years == 2
    assert extraction.experience_max_years == 4


def test_empty_input_returns_empty_extraction() -> None:
    extraction = JobExtractor().extract("")
    assert extraction.required_skills == []
    assert extraction.experience_min_years is None
