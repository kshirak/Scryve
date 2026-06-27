"""Shared fixtures for the intelligence-layer test suite."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest


def _today_minus(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


@pytest.fixture
def sample_record() -> dict[str, Any]:
    """A representative candidate record covering all parser pathways."""
    return {
        "candidate_id": "CAND_0001234",
        "name": "Riya Sharma",
        "current_title": "Senior Machine Learning Engineer",
        "current_company": "Acme AI",
        "location": "Pune, India",
        "total_experience_years": 6.5,
        "summary": "Built embedding-based retrieval at scale; hybrid BM25 + dense.",
        "email": "riya@example.com",
        "skills": [
            {"name": "Python", "proficiency": "expert", "years_used": 7},
            {"name": "FAISS", "proficiency": 85, "years_used": 3},
            {"name": "Sentence-Transformers", "proficiency": 0.8},
            "Elasticsearch",
        ],
        "experience": [
            {
                "company": "Acme AI",
                "title": "Senior Machine Learning Engineer",
                "start_date": "2022-04-01",
                "end_date": None,
                "description": "Owns retrieval and ranking; ships A/B tests.",
                "location": "Pune",
            },
            {
                "company": "BetaSearch",
                "title": "Machine Learning Engineer",
                "start_date": "2019-06-01",
                "end_date": "2022-03-31",
                "description": "Built BM25 + dense hybrid search.",
            },
            {
                "company": "GammaLabs",
                "title": "Junior Data Scientist",
                "start_date": "2017-08-01",
                "end_date": "2019-05-31",
            },
        ],
        "education": [
            {
                "institution": "IIT Bombay",
                "degree": "Master of Technology",
                "field_of_study": "Computer Science",
                "end_year": 2017,
            },
            {
                "institution": "BITS Pilani",
                "degree": "Bachelor of Engineering",
                "field_of_study": "Computer Science",
                "end_year": 2015,
            },
        ],
        "certifications": [
            {"name": "AWS Machine Learning Specialty", "issued_year": 2023},
        ],
        "languages": [
            {"name": "English", "proficiency": "fluent"},
            "Hindi",
        ],
        "redrob_signals": {
            "profile_completeness_score": 88,
            "signup_date": "2020-01-15",
            "last_active_date": _today_minus(5),
            "open_to_work_flag": True,
            "profile_views_received_30d": 42,
            "applications_submitted_30d": 3,
            "recruiter_response_rate": 0.78,
            "avg_response_time_hours": 6.2,
            "skill_assessment_scores": {"Python": 92, "FAISS": 81},
            "connection_count": 850,
            "endorsements_received": 120,
            "notice_period_days": 30,
            "expected_salary_range_inr_lpa": {"min": 35, "max": 55},
            "preferred_work_mode": "hybrid",
            "willing_to_relocate": True,
            "github_activity_score": 78,
            "search_appearance_30d": 35,
            "saved_by_recruiters_30d": 6,
            "interview_completion_rate": 0.9,
            "offer_acceptance_rate": 0.5,
            "verified_email": True,
            "verified_phone": True,
            "linkedin_connected": True,
        },
    }


@pytest.fixture
def weak_record() -> dict[str, Any]:
    """A profile that should rank low (keyword-stuffed Marketing Manager)."""
    return {
        "candidate_id": "CAND_0099999",
        "name": "Generic Person",
        "current_title": "Marketing Manager",
        "current_company": "ConsultCo",
        "location": "Bangalore",
        "total_experience_years": 12.0,
        "skills": [
            "Python",
            "FAISS",
            "Embeddings",
            "LangChain",
            "RAG",
            "Pinecone",
            "OpenAI",
            "Vector Search",
        ],
        "experience": [
            {
                "company": "ConsultCo",
                "title": "Marketing Manager",
                "start_date": "2014-01-01",
                "end_date": None,
            }
        ],
        "education": [{"degree": "Bachelor of Commerce", "end_year": 2013}],
        "redrob_signals": {
            "profile_completeness_score": 45,
            "last_active_date": _today_minus(200),
            "open_to_work_flag": False,
            "recruiter_response_rate": 0.05,
            "notice_period_days": 90,
            "willing_to_relocate": False,
            "interview_completion_rate": 0.2,
        },
    }
