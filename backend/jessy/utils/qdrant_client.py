"""Minimal Qdrant integration for storing document embeddings."""

from __future__ import annotations

import os
import uuid
from typing import Any

_COLLECTION_NAME = "documents"
_QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")

_client = None


def get_qdrant_client():
    """Return a cached Qdrant client instance (lazy import)."""
    global _client

    if _client is None:
        from qdrant_client import QdrantClient

        _client = QdrantClient(url=_QDRANT_URL)

    return _client


def initialize_qdrant(collection_name: str = _COLLECTION_NAME):
    """Connect to Qdrant and create the target collection if needed."""
    from qdrant_client.http import models as rest_models

    client = get_qdrant_client()

    try:
        collections = client.get_collections()
        existing_names = {collection.name for collection in collections.collections}

        if collection_name not in existing_names:
            client.create_collection(
                collection_name=collection_name,
                vectors_config=rest_models.VectorParams(
                    size=384,
                    distance=rest_models.Distance.COSINE,
                ),
            )
    except Exception as exc:  # noqa: BLE001
        print(f"Qdrant initialization warning: {exc}")

    return client


def store_embeddings(
    chunks: list[dict[str, Any]],
    collection_name: str = _COLLECTION_NAME,
) -> int:
    """Store embedding-backed document chunks into Qdrant."""
    if not chunks:
        return 0

    try:
        client = initialize_qdrant(collection_name)
        points: list[dict[str, Any]] = []

        for chunk in chunks:
            embedding = chunk.get("embedding")
            if not embedding:
                continue

            points.append(
                {
                    "id": str(uuid.uuid4()),
                    "vector": embedding,
                    "payload": {
                        "document_id": chunk.get("document_id"),
                        "file_name": chunk.get("file_name"),
                        "chunk_index": chunk.get("chunk_index"),
                        "content": chunk.get("content"),
                    },
                }
            )

        if points:
            client.upsert(collection_name=collection_name, points=points)

        return len(points)
    except Exception as exc:  # noqa: BLE001
        print(f"Qdrant storage warning: {exc}")
        return 0
