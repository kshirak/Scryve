"""Skill alias resolution and normalization.

The normalizer collapses common skill name variants to a single canonical
form so that downstream matchers compare like-for-like. It is also aware
of the :data:`SKILL_TAXONOMY` so it can tell which category a normalized
skill belongs to (programming language, framework, domain, ...).

The alias map is hand-curated. Keeping it explicit (rather than building
a fuzzy synonym model) makes false-positive matches rare and
recruiter-debuggable — the most important property for a ranking signal.
"""

from __future__ import annotations

import re
from difflib import get_close_matches
from typing import Final, Iterable

from app.intelligence.skills.taxonomy import SKILL_TAXONOMY, SkillCategory

# ----------------------------------------------------------------------
# Curated alias map.
# Keys are normalized lookup forms (lower-cased, no internal punctuation
# beyond what survives ``_normalize_lookup``); values are the canonical
# skill names that appear in :data:`SKILL_TAXONOMY`.
# ----------------------------------------------------------------------
SKILL_ALIASES: Final[dict[str, str]] = {
    # Languages
    "py": "Python",
    "python3": "Python",
    "python 3": "Python",
    "js": "JavaScript",
    "ecmascript": "JavaScript",
    "node": "JavaScript",
    "nodejs": "JavaScript",
    "node.js": "JavaScript",
    "ts": "TypeScript",
    "cpp": "C++",
    "c plus plus": "C++",
    "c sharp": "C#",
    "csharp": "C#",
    "golang": "Go",
    "rustlang": "Rust",
    "kotlinlang": "Kotlin",
    "objective-c": "Swift",  # close-enough mapping for resumes

    # Web frameworks
    "react.js": "React",
    "reactjs": "React",
    "react js": "React",
    "vue": "Vue.js",
    "vuejs": "Vue.js",
    "next": "Next.js",
    "nextjs": "Next.js",
    "nest": "Nest.js",
    "nestjs": "Nest.js",
    "express": "Express.js",
    "expressjs": "Express.js",
    "rails": "Ruby on Rails",
    "ror": "Ruby on Rails",
    "dotnet": ".NET",
    ".net core": ".NET",
    "asp .net": "ASP.NET",
    "aspnet": "ASP.NET",
    "spring": "Spring Boot",
    "springboot": "Spring Boot",

    # Python web frameworks
    "django rest framework": "Django",
    "drf": "Django",
    "fast api": "FastAPI",
    "fastapi framework": "FastAPI",

    # Data / ML
    "sklearn": "scikit-learn",
    "scikit learn": "scikit-learn",
    "tf": "TensorFlow",
    "tensor flow": "TensorFlow",
    "torch": "PyTorch",
    "pytorch lightning": "PyTorch",
    "huggingface": "Hugging Face Transformers",
    "hugging face": "Hugging Face Transformers",
    "transformers": "Hugging Face Transformers",
    "lang chain": "LangChain",
    "llama index": "LlamaIndex",
    "spacy": "spaCy",
    "open cv": "OpenCV",
    "pandas dataframe": "Pandas",
    "numpy array": "NumPy",
    "sentence transformers": "Sentence-Transformers",
    "sbert": "Sentence-Transformers",
    "bge": "Sentence-Transformers",
    "e5": "Sentence-Transformers",

    # Vector / search
    "facebook ai similarity search": "FAISS",
    "elastic search": "Elasticsearch",
    "elastic": "Elasticsearch",
    "open search": "OpenSearch",
    "vector db": "Vector Search",
    "vector database": "Vector Search",
    "hybrid retrieval": "Hybrid Search",

    # Databases
    "postgres": "PostgreSQL",
    "psql": "PostgreSQL",
    "postgre sql": "PostgreSQL",
    "mysql db": "MySQL",
    "mongo": "MongoDB",
    "mongo db": "MongoDB",
    "big query": "BigQuery",
    "dynamo db": "DynamoDB",
    "redis cache": "Redis",

    # Cloud
    "amazon web services": "AWS",
    "aws cloud": "AWS",
    "google cloud": "GCP",
    "google cloud platform": "GCP",
    "ms azure": "Azure",
    "microsoft azure": "Azure",

    # DevOps / data infra
    "k8s": "Kubernetes",
    "kube": "Kubernetes",
    "tf cloud": "Terraform",
    "github action": "GitHub Actions",
    "gh actions": "GitHub Actions",
    "apache airflow": "Airflow",
    "apache kafka": "Kafka",
    "apache spark": "Spark",
    "apache hadoop": "Hadoop",
    "rest apis": "REST API",
    "restful": "REST API",
    "restful apis": "REST API",
    "rest": "REST API",
    "graph ql": "GraphQL",
    "grpc": "gRPC",

    # Methodologies
    "agile methodology": "Agile",
    "scrum methodology": "Scrum",
    "test driven development": "TDD",
    "ci-cd": "CI/CD",
    "ci cd": "CI/CD",
    "continuous integration": "CI/CD",
    "continuous deployment": "CI/CD",

    # Domain
    "ml": "Machine Learning",
    "machine-learning": "Machine Learning",
    "dl": "Deep Learning",
    "deep-learning": "Deep Learning",
    "nlp": "Natural Language Processing",
    "natural-language-processing": "Natural Language Processing",
    "cv": "Computer Vision",
    "ir": "Information Retrieval",
    "recsys": "Recommendation Systems",
    "recommender systems": "Recommendation Systems",
    "ltr": "Learning to Rank",
    "learning-to-rank": "Learning to Rank",
    "vector search": "Vector Search",
    "rag systems": "RAG",
    "retrieval augmented generation": "RAG",
    "retrieval-augmented generation": "RAG",
    "fine tuning": "LLM Fine-tuning",
    "fine-tuning": "LLM Fine-tuning",
    "llm fine tuning": "LLM Fine-tuning",
    "lora fine tuning": "LoRA",
    "qlora fine tuning": "QLoRA",
    "ab testing": "A/B Testing",
    "a-b testing": "A/B Testing",
    "ab test": "A/B Testing",
    "mlops practices": "MLOps",
    "ml ops": "MLOps",
    "data eng": "Data Engineering",
}


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------
_PUNCTUATION_RE = re.compile(r"[^a-z0-9+#./\- ]")
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_lookup(value: str) -> str:
    """Return a normalized lookup key for alias matching.

    The form is lower-cased, collapses internal whitespace, and strips
    punctuation other than the few characters that are meaningful in
    skill names (``+ # . / -``). It is deliberately *not* the user-
    visible canonical form — that comes from the taxonomy.
    """
    lowered = value.strip().lower()
    cleaned = _PUNCTUATION_RE.sub(" ", lowered)
    return _WHITESPACE_RE.sub(" ", cleaned).strip()


def _build_canonical_index() -> dict[str, str]:
    """Index canonical names by their normalized lookup form."""
    return {_normalize_lookup(name): name for name in SKILL_TAXONOMY}


_CANONICAL_INDEX: Final[dict[str, str]] = _build_canonical_index()
_ALIAS_INDEX: Final[dict[str, str]] = {
    _normalize_lookup(alias): canonical for alias, canonical in SKILL_ALIASES.items()
}


# ----------------------------------------------------------------------
# Public API
# ----------------------------------------------------------------------
class SkillNormalizer:
    """Normalize raw skill strings to canonical forms.

    Resolution order, first match wins:

    1. Exact match against the curated alias map.
    2. Exact match against the canonical taxonomy (case-insensitive).
    3. Optional fuzzy match against canonical names (cutoff configurable).
    4. Best-effort title-casing of the raw input (so unknown skills still
       come out tidy).
    """

    def __init__(
        self,
        *,
        fuzzy: bool = True,
        fuzzy_cutoff: float = 0.9,
        extra_aliases: dict[str, str] | None = None,
    ) -> None:
        """Initialize the normalizer.

        Args:
            fuzzy: When True, fall back to ``difflib.get_close_matches``
                for unknown skills.
            fuzzy_cutoff: Similarity cutoff in [0, 1] for fuzzy matches.
            extra_aliases: Project-specific aliases merged on top of the
                curated map. Keys may be raw strings; they are normalized
                internally.
        """
        self.fuzzy = fuzzy
        self.fuzzy_cutoff = fuzzy_cutoff

        self._alias_index: dict[str, str] = dict(_ALIAS_INDEX)
        if extra_aliases:
            for alias, canonical in extra_aliases.items():
                self._alias_index[_normalize_lookup(alias)] = canonical
        self._canonical_index = _CANONICAL_INDEX
        self._canonical_lookup_keys: list[str] = list(self._canonical_index.keys())

    # ------------------------------------------------------------------
    # Single value
    # ------------------------------------------------------------------
    def normalize(self, raw: str) -> str:
        """Return the canonical name for a raw skill string.

        Args:
            raw: Raw skill text (e.g. ``"Postgres"``).

        Returns:
            Canonical skill name (e.g. ``"PostgreSQL"``). Unknown skills
            are returned title-cased so output is presentation-friendly.
        """
        if not raw or not raw.strip():
            return ""

        lookup = _normalize_lookup(raw)

        canonical = self._alias_index.get(lookup)
        if canonical:
            return canonical

        canonical = self._canonical_index.get(lookup)
        if canonical:
            return canonical

        if self.fuzzy:
            matches = get_close_matches(
                lookup,
                self._canonical_lookup_keys,
                n=1,
                cutoff=self.fuzzy_cutoff,
            )
            if matches:
                return self._canonical_index[matches[0]]

        # Unknown — keep the user's casing if it already looks intentional,
        # otherwise title-case.
        stripped = raw.strip()
        if any(ch.isupper() for ch in stripped[1:]):
            return stripped
        return stripped.title()

    # ------------------------------------------------------------------
    # Batch helpers
    # ------------------------------------------------------------------
    def normalize_many(self, raws: Iterable[str]) -> list[str]:
        """Normalize a batch and deduplicate while preserving order."""
        seen: set[str] = set()
        out: list[str] = []
        for raw in raws:
            canonical = self.normalize(raw)
            if not canonical:
                continue
            key = canonical.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(canonical)
        return out

    def is_known(self, raw: str) -> bool:
        """True when the raw value resolves to a known canonical skill."""
        if not raw or not raw.strip():
            return False
        lookup = _normalize_lookup(raw)
        return lookup in self._alias_index or lookup in self._canonical_index

    def category_of(self, raw: str) -> SkillCategory | None:
        """Return the taxonomy category for a raw skill, if known."""
        canonical = self.normalize(raw)
        return SKILL_TAXONOMY.get(canonical)


__all__ = ["SKILL_ALIASES", "SkillCategory", "SkillNormalizer"]
