"""Tests for the Phase-3 embedding backends."""

from __future__ import annotations

import math

import pytest

from app.intelligence.embeddings.embedder import (
    EmbeddingResult,
    HashingEmbedder,
)


@pytest.fixture
def embedder() -> HashingEmbedder:
    return HashingEmbedder(dimension=128, model_name="hashing-test")


def test_embedder_returns_metadata(embedder: HashingEmbedder) -> None:
    result = embedder.embed("Python Django PostgreSQL backend engineer")

    assert isinstance(result, EmbeddingResult)
    assert result.model_name == "hashing-test"
    assert result.dimension == 128
    assert len(result.vector) == 128


def test_embedder_is_deterministic(embedder: HashingEmbedder) -> None:
    text = "Senior AI engineer with vector search and embeddings"
    a = embedder.embed(text).vector
    b = embedder.embed(text).vector
    assert a == b


def test_embedder_produces_unit_norm_vector(embedder: HashingEmbedder) -> None:
    vec = embedder.embed("Python backend engineer").vector
    norm = math.sqrt(sum(v * v for v in vec))
    assert norm == pytest.approx(1.0, abs=1e-5)


def test_similar_texts_have_higher_dot_product_than_dissimilar() -> None:
    embedder = HashingEmbedder(dimension=512)

    job = embedder.embed(
        "Python Django PostgreSQL REST API backend engineer with CI/CD"
    ).vector
    similar = embedder.embed(
        "Backend developer using Python Django and PostgreSQL for REST APIs"
    ).vector
    unrelated = embedder.embed(
        "Marketing manager focused on brand storytelling and ad campaigns"
    ).vector

    def dot(a: list[float], b: list[float]) -> float:
        return sum(x * y for x, y in zip(a, b))

    sim_close = dot(job, similar)
    sim_far = dot(job, unrelated)
    assert sim_close > sim_far


def test_embed_many_returns_one_result_per_text(embedder: HashingEmbedder) -> None:
    results = embedder.embed_many(["python", "django", "postgres"])
    assert len(results) == 3
    assert all(r.dimension == 128 for r in results)


def test_empty_text_yields_zero_vector(embedder: HashingEmbedder) -> None:
    result = embedder.embed("")
    assert all(v == 0.0 for v in result.vector)


def test_invalid_dimension_raises() -> None:
    with pytest.raises(ValueError):
        HashingEmbedder(dimension=0)
