"""Sanity tests for the health-check endpoint."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import settings


def test_health_endpoint_returns_ok(client: TestClient) -> None:
    """`GET /api/v1/health` returns a 200 with the service metadata."""
    response = client.get(f"{settings.api_v1_prefix}/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == settings.app_name
    assert payload["environment"] == settings.app_env
    assert "version" in payload


def test_root_endpoint(client: TestClient) -> None:
    """Root endpoint returns a small descriptor payload."""
    response = client.get("/")
    assert response.status_code == 200
    payload = response.json()
    assert payload["service"] == settings.app_name
    assert payload["docs"] == "/docs"
