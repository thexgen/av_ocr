"""Minimal semantic search over stored document embeddings."""

from __future__ import annotations

from typing import Any

from backend.jessy.utils.embedding_generator import get_embedding_model
from backend.jessy.utils.qdrant_client import get_qdrant_client, initialize_qdrant

_COLLECTION_NAME = "documents"


def search_similar_chunks(question: str, limit: int = 5) -> list[dict[str, Any]]:
    """Return the top similar chunks for a user question from Qdrant."""
    if not question.strip():
        return []

    try:
        initialize_qdrant(_COLLECTION_NAME)
        model = get_embedding_model()
        query_embedding = model.encode([question], normalize_embeddings=True)[0]

        client = get_qdrant_client()
        query_method = getattr(client, "query_points", None)
        if callable(query_method):
            response = query_method(
                collection_name=_COLLECTION_NAME,
                query=query_embedding,
                limit=limit,
                with_payload=True,
            )
            results = getattr(response, "points", response)
        else:
            results = client.search(
                collection_name=_COLLECTION_NAME,
                query_vector=query_embedding,
                limit=limit,
                with_payload=True,
            )

        matches: list[dict[str, Any]] = []
        for result in results:
            payload = result.payload or {}
            matches.append(
                {
                    "document_id": payload.get("document_id"),
                    "file_name": payload.get("file_name"),
                    "chunk_index": payload.get("chunk_index"),
                    "content": payload.get("content", ""),
                    "score": float(getattr(result, "score", 0.0)),
                }
            )

        return matches
    except Exception as exc:  # noqa: BLE001
        print(f"Semantic search warning: {exc}")
        return []
