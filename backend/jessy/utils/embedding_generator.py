"""Local text embedding helpers for document chunks."""

from __future__ import annotations

from typing import Any

_MODEL = None


def get_embedding_model():
    """Return a cached sentence-transformers model instance (lazy import)."""
    global _MODEL

    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5")

    return _MODEL


def generate_embeddings(chunks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add local embeddings to each chunk dictionary in place."""
    if not chunks:
        return chunks

    texts = [chunk["content"] for chunk in chunks]
    model = get_embedding_model()
    embeddings = model.encode(texts, normalize_embeddings=True)

    for chunk, embedding in zip(chunks, embeddings):
        if hasattr(embedding, "tolist"):
            chunk["embedding"] = embedding.tolist()
        else:
            chunk["embedding"] = list(embedding)

    return chunks
