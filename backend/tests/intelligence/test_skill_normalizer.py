"""Unit tests for the skill normalizer."""

from __future__ import annotations

import pytest

from app.intelligence.skills import SkillCategory, SkillNormalizer


@pytest.fixture
def normalizer() -> SkillNormalizer:
    return SkillNormalizer()


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Postgres", "PostgreSQL"),
        ("postgres", "PostgreSQL"),
        ("PSQL", "PostgreSQL"),
        ("React.js", "React"),
        ("reactjs", "React"),
        ("React", "React"),
        ("Py", "Python"),
        ("python3", "Python"),
        ("Python 3", "Python"),
        ("PYTHON", "Python"),
        ("Node.js", "JavaScript"),
        ("k8s", "Kubernetes"),
        ("aws cloud", "AWS"),
        ("Google Cloud", "GCP"),
        ("ML", "Machine Learning"),
        ("nlp", "Natural Language Processing"),
        ("ltr", "Learning to Rank"),
        ("Sentence Transformers", "Sentence-Transformers"),
        ("RAG", "RAG"),
        ("Fine-Tuning", "LLM Fine-tuning"),
        ("REST APIs", "REST API"),
    ],
)
def test_aliases_resolve_to_canonical(normalizer, raw, expected):
    assert normalizer.normalize(raw) == expected


def test_unknown_skill_is_title_cased(normalizer):
    assert normalizer.normalize("some niche framework") == "Some Niche Framework"


def test_normalize_many_dedupes_and_preserves_order(normalizer):
    out = normalizer.normalize_many(
        ["Postgres", "PostgreSQL", "psql", "react.js", "React"]
    )
    assert out == ["PostgreSQL", "React"]


def test_is_known_returns_true_for_aliases(normalizer):
    assert normalizer.is_known("Postgres")
    assert normalizer.is_known("python3")
    assert not normalizer.is_known("this-is-not-a-skill-anywhere")


def test_category_of_returns_taxonomy_bucket(normalizer):
    assert normalizer.category_of("Postgres") is SkillCategory.DATABASE
    assert normalizer.category_of("Python") is SkillCategory.PROGRAMMING_LANGUAGE
    assert normalizer.category_of("FastAPI") is SkillCategory.FRAMEWORK
    assert normalizer.category_of("RAG") is SkillCategory.DOMAIN
    assert normalizer.category_of("totally-unknown-thing") is None


def test_extra_aliases_are_honored():
    custom = SkillNormalizer(extra_aliases={"pgsql": "PostgreSQL"})
    assert custom.normalize("pgsql") == "PostgreSQL"


def test_empty_string_returns_empty(normalizer):
    assert normalizer.normalize("") == ""
    assert normalizer.normalize("   ") == ""
