"""Simple text chunking utilities."""

from typing import Any


def chunk_text(text: str, document_id: str, file_name: str) -> list[dict[str, Any]]:
    """Split text into ordered chunks with overlap (size=1000, overlap=200)."""
    chunk_size = 1000
    overlap = 200
    step = chunk_size - overlap

    if not text:
        return []

    chunks: list[dict[str, Any]] = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk_content = text[start:end]
        chunks.append(
            {
                "document_id": document_id,
                "file_name": file_name,
                "chunk_index": len(chunks),
                "content": chunk_content,
            }
        )

        if end >= len(text):
            break

        start += step

    return chunks
