from __future__ import annotations

import logging

import fitz

from backend.config import TEXT_PDF_CHAR_THRESHOLD, cfg
from backend.exceptions import (
    CorruptedPDFError,
    EmptyPDFError,
    MaxPagesExceededError,
    PasswordProtectedPDFError,
)

logger = logging.getLogger("holding_engine")


def open_pdf_document(pdf_bytes: bytes) -> fitz.Document:
    """Open PDF from bytes with production failure classification."""
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise EmptyPDFError("PDF file is empty (0 bytes)")

    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    except Exception as exc:  # noqa: BLE001
        msg = str(exc).lower()
        if "password" in msg or "encrypted" in msg:
            raise PasswordProtectedPDFError(
                "PDF is password protected or encrypted"
            ) from exc
        raise CorruptedPDFError(f"PDF appears corrupted or unreadable: {exc}") from exc

    try:
        if doc.is_encrypted:
            # Try empty password; if still needs auth, fail gracefully
            auth = doc.authenticate("")
            if not auth and doc.needs_pass:
                doc.close()
                raise PasswordProtectedPDFError("PDF is password protected")

        if doc.page_count == 0:
            doc.close()
            raise EmptyPDFError("PDF has zero pages")

        max_pages = int(cfg("processing", "max_pages", default=100))
        if doc.page_count > max_pages:
            count = doc.page_count
            doc.close()
            raise MaxPagesExceededError(
                f"PDF has {count} pages; max allowed is {max_pages}"
            )
    except (EmptyPDFError, PasswordProtectedPDFError, MaxPagesExceededError):
        raise
    except Exception as exc:  # noqa: BLE001
        try:
            doc.close()
        except Exception:  # noqa: BLE001
            pass
        raise CorruptedPDFError(f"Failed to inspect PDF: {exc}") from exc

    return doc


def detect_pdf_type(pdf_bytes: bytes, source_label: str = "input") -> tuple[str, dict]:
    """
    Detect whether a PDF is text-based or scanned/image-based.
    Raises ProcessingError subclasses for empty/corrupt/password/max-pages.
    """
    logger.info("Detecting PDF type for %s (%s bytes)", source_label, len(pdf_bytes))
    doc = open_pdf_document(pdf_bytes)
    try:
        page_count = doc.page_count
        total_chars = 0
        page_chars: list[int] = []
        threshold = int(TEXT_PDF_CHAR_THRESHOLD)

        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            n = len(text.strip())
            page_chars.append(n)
            total_chars += n
            logger.info("Page %s text chars: %s", i + 1, n)

        avg = (total_chars / page_count) if page_count else 0
        pdf_type = "text" if avg >= threshold else "scanned"

        stats = {
            "page_count": page_count,
            "total_chars": total_chars,
            "avg_chars_per_page": round(avg, 2),
            "threshold": threshold,
            "page_chars": page_chars,
        }
        logger.info(
            "PDF type=%s (avg_chars=%.2f, threshold=%s)",
            pdf_type,
            avg,
            threshold,
        )
        return pdf_type, stats
    finally:
        doc.close()
