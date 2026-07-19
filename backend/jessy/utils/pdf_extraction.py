"""Utility helpers for PDF processing."""

from pathlib import Path

import fitz


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract all text from a PDF file using PyMuPDF."""
    text_parts: list[str] = []

    with fitz.open(pdf_path) as document:
        for page_number in range(document.page_count):
            page = document.load_page(page_number)
            page_text = page.get_text()
            if page_text:
                text_parts.append(page_text)

    return "\n".join(text_parts).strip()
