"""Jessy knowledge document upload — PDF → extract → chunk → embed → Qdrant."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from backend.jessy.utils.embedding_generator import generate_embeddings
from backend.jessy.utils.pdf_extraction import extract_text_from_pdf
from backend.jessy.utils.qdrant_client import store_embeddings
from backend.jessy.utils.text_chunker import chunk_text

router = APIRouter(prefix="/documents", tags=["jessy-documents"])

UPLOAD_DIR: Path = Path(__file__).resolve().parents[1] / "uploads"


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)) -> JSONResponse:
    """Accept a PDF, run the Jessy ingest pipeline, store vectors in Qdrant."""
    original_name = Path(file.filename or "").name

    if not original_name.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="Only PDF files are allowed.",
        )

    contents = await file.read()
    if not contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty.",
        )

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    stem = Path(original_name).stem
    suffix = Path(original_name).suffix
    stored_name = f"{stem}_{uuid.uuid4().hex[:8]}{suffix}"
    target_path = UPLOAD_DIR / stored_name

    with target_path.open("wb") as handle:
        handle.write(contents)

    size = target_path.stat().st_size
    extracted_text = extract_text_from_pdf(target_path)

    chunks_stored = 0
    if extracted_text:
        chunks = chunk_text(extracted_text, stored_name, original_name)
        chunks = generate_embeddings(chunks)
        chunks_stored = store_embeddings(chunks)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No extractable text found in the uploaded PDF.",
        )

    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "success": True,
            "file_name": original_name,
            "stored_name": stored_name,
            "size": size,
            "chunks_stored": chunks_stored,
        },
    )
