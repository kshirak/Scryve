"""Shared pytest fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture(scope="session")
def client() -> Iterator[TestClient]:
    """Provide a FastAPI test client backed by a fresh app instance."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
