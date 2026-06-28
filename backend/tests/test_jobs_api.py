"""Smoke tests for the Phase-3 Jobs HTTP surface.

The full create-job flow requires Postgres (the Job model uses
``ARRAY``/``JSONB``/``UUID``), so this suite only exercises the
DB-free endpoint — ``POST /api/v1/jobs/extract`` — which still verifies
that routing, dependency injection, and the service wiring all work.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.v1.endpoints.jobs import get_job_service
from app.dependencies import get_db_session
from app.main import create_app
from app.services import JobService


@pytest.fixture
def client() -> TestClient:
    app = create_app()

    def _no_db():
        # Phase-3 extract is DB-free; provide a placeholder.
        yield None

    def _service_without_db() -> JobService:
        # Build a JobService that never touches the database. The
        # extractor is the only thing the /extract endpoint needs.
        return JobService(db=None, repository=None)  # type: ignore[arg-type]

    app.dependency_overrides[get_db_session] = _no_db
    app.dependency_overrides[get_job_service] = _service_without_db
    return TestClient(app)


def test_extract_endpoint_returns_structured_response(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs/extract",
        json={
            "title": "Backend Developer",
            "description": (
                "Looking for Python Django developer with PostgreSQL "
                "experience and REST API knowledge. 2-4 years experience."
            ),
            "generate_embedding": False,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Backend Developer"
    assert "Python" in body["required_skills"]
    assert "Django" in body["required_skills"]
    assert "PostgreSQL" in body["required_skills"]
    assert "REST API" in body["required_skills"]
    assert body["experience_min_years"] == 2
    assert body["experience_max_years"] == 4


def test_extract_endpoint_validates_input(client: TestClient) -> None:
    response = client.post(
        "/api/v1/jobs/extract",
        json={"description": "too short"},
    )
    assert response.status_code == 422
