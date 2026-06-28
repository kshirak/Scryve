"""Text embedding backends used by the job-intelligence module.

Two backends are supported:

* :class:`HashingEmbedder` (default) — deterministic, dependency-free,
  CPU-friendly. Implements the classic *feature-hashing trick*: each
  token (and bigram) of the input is hashed to a slot in a fixed-size
  vector with a stable sign, then the result is L2-normalized so that
  cosine similarity equals the dot product. This gives perfectly
  reproducible vectors that are good enough for keyword-oriented
  matching, and trivially compatible with FAISS ``IndexFlatIP``.

* :class:`SentenceTransformerEmbedder` — optional. Loaded only if the
  caller selects ``EMBEDDING_BACKEND=sentence-transformers`` *and*
  ``sentence-transformers`` is installed. Produces real semantic
  embeddings (``all-MiniLM-L6-v2`` by default), at the cost of pulling
  in PyTorch.

Both backends emit ``EmbeddingResult`` instances so the persistence
layer stores enough metadata (model name, dimension) to rebuild a FAISS
index later.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np

from app.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9+.#/-]*")


@dataclass(frozen=True)
class EmbeddingResult:
    """A produced embedding plus the metadata FAISS needs later."""

    vector: list[float]
    model_name: str
    dimension: int
    source_text: str = field(repr=False)


class Embedder(Protocol):
    """Common protocol implemented by every embedding backend."""

    model_name: str
    dimension: int

    def embed(self, text: str) -> EmbeddingResult: ...

    def embed_many(self, texts: list[str]) -> list[EmbeddingResult]: ...


# ----------------------------------------------------------------------
# Deterministic hashing backend
# ----------------------------------------------------------------------
class HashingEmbedder:
    """Deterministic feature-hashing embedder.

    Tokens and adjacent token bigrams are hashed with MD5 to obtain a
    stable slot index plus a ±1 sign per feature. The resulting vector
    is L2-normalized so cosine similarity reduces to a dot product —
    the form FAISS ``IndexFlatIP`` indexes natively.

    The hashing trick produces vectors that:

    * Are deterministic across machines (no ``PYTHONHASHSEED`` reliance).
    * Don't require any model download or torch dependency.
    * Are dimension-configurable (defaults to 384, matching MiniLM).

    For richer semantic similarity, switch the backend via
    ``EMBEDDING_BACKEND=sentence-transformers``.
    """

    def __init__(
        self,
        *,
        dimension: int = 384,
        model_name: str = "hashing-v1",
    ) -> None:
        if dimension <= 0:
            raise ValueError("dimension must be positive")
        self.dimension = dimension
        self.model_name = model_name

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def embed(self, text: str) -> EmbeddingResult:
        """Embed a single text blob."""
        vec = self._vectorize(text)
        return EmbeddingResult(
            vector=vec.tolist(),
            model_name=self.model_name,
            dimension=self.dimension,
            source_text=text,
        )

    def embed_many(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed a batch of texts."""
        return [self.embed(t) for t in texts]

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _vectorize(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dimension, dtype=np.float32)
        if not text or not text.strip():
            return vec

        tokens = _TOKEN_RE.findall(text.lower())
        if not tokens:
            return vec

        # Unigrams.
        for token in tokens:
            slot, sign = self._slot_and_sign(token)
            vec[slot] += sign

        # Bigrams capture short phrases like "vector search" / "fine tuning".
        for left, right in zip(tokens, tokens[1:]):
            slot, sign = self._slot_and_sign(f"{left}_{right}")
            vec[slot] += sign

        norm = float(np.linalg.norm(vec))
        if norm > 0:
            vec = vec / norm
        return vec

    def _slot_and_sign(self, token: str) -> tuple[int, float]:
        """Map ``token`` to ``(slot_index, sign)`` using MD5."""
        digest = hashlib.md5(token.encode("utf-8")).digest()
        slot = int.from_bytes(digest[:4], "big") % self.dimension
        sign = 1.0 if (digest[4] & 1) else -1.0
        return slot, sign


# ----------------------------------------------------------------------
# Optional sentence-transformers backend
# ----------------------------------------------------------------------
class SentenceTransformerEmbedder:
    """Wrapper around ``sentence-transformers`` for richer semantics.

    Lazily imports the package so the rest of the codebase remains
    importable without it installed. Vectors are L2-normalized so they
    can be combined freely with :class:`HashingEmbedder` outputs in
    FAISS ``IndexFlatIP``.
    """

    def __init__(
        self,
        *,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:  # pragma: no cover - optional dep
            raise ImportError(
                "EMBEDDING_BACKEND=sentence-transformers requires the "
                "`sentence-transformers` package to be installed."
            ) from exc

        self._model = SentenceTransformer(model_name)
        self.model_name = model_name
        self.dimension = int(self._model.get_sentence_embedding_dimension())

    def embed(self, text: str) -> EmbeddingResult:
        """Embed a single text blob."""
        vec = self._model.encode([text or ""], normalize_embeddings=True)[0]
        return EmbeddingResult(
            vector=[float(x) for x in vec.tolist()],
            model_name=self.model_name,
            dimension=self.dimension,
            source_text=text,
        )

    def embed_many(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed a batch of texts in a single forward pass."""
        encoded = self._model.encode(
            [t or "" for t in texts],
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
        return [
            EmbeddingResult(
                vector=[float(x) for x in row.tolist()],
                model_name=self.model_name,
                dimension=self.dimension,
                source_text=texts[i],
            )
            for i, row in enumerate(encoded)
        ]


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------
def build_embedder() -> Embedder:
    """Build the embedder selected by application settings.

    The backend is chosen from ``settings.embedding_backend``. The
    function returns the singleton-friendly instance directly — callers
    should reuse it across requests because the ST backend is expensive
    to construct.
    """
    backend = settings.embedding_backend.lower()
    if backend == "sentence-transformers":
        logger.info(
            "embedder.backend.selected",
            backend="sentence-transformers",
            model=settings.embedding_model_name,
        )
        return SentenceTransformerEmbedder(model_name=settings.embedding_model_name)

    logger.info(
        "embedder.backend.selected",
        backend="hashing",
        dimension=settings.embedding_dimension,
    )
    return HashingEmbedder(
        dimension=settings.embedding_dimension,
        model_name=settings.embedding_model_name,
    )


__all__ = [
    "Embedder",
    "EmbeddingResult",
    "HashingEmbedder",
    "SentenceTransformerEmbedder",
    "build_embedder",
]
