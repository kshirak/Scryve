"""Text embedding backends used across phases.

Phase 3 (Job Intelligence) ships:

* :class:`HashingEmbedder` — dependency-free deterministic embedder.
* :class:`SentenceTransformerEmbedder` — optional richer backend.
* :func:`build_embedder` — factory that honours
  ``settings.embedding_backend``.

Vectors are L2-normalized so cosine similarity reduces to a dot product,
which means they can be indexed directly with FAISS ``IndexFlatIP`` in
Phase 4.
"""

from app.intelligence.embeddings.embedder import (
    Embedder,
    EmbeddingResult,
    HashingEmbedder,
    SentenceTransformerEmbedder,
    build_embedder,
)

__all__ = [
    "Embedder",
    "EmbeddingResult",
    "HashingEmbedder",
    "SentenceTransformerEmbedder",
    "build_embedder",
]
