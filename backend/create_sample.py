from __future__ import annotations

import logging

import fitz

from backend.config import SAMPLE_DATA_PREFIX
from backend.interfaces.storage import StorageService

logger = logging.getLogger("holding_poc")

DEFAULT_SAMPLE_KEY = f"{SAMPLE_DATA_PREFIX}/sample_holding_statement.pdf"


def create_sample_holding_pdf(
    storage: StorageService,
    key: str = DEFAULT_SAMPLE_KEY,
) -> str:
    """
    Create a sample text holding PDF and save it via StorageService.
    Returns the storage key.
    """
    logger.info("STEP | Creating sample holding PDF -> storage key=%s", key)

    doc = fitz.open()
    page = doc.new_page(width=595, height=842)

    lines = [
        ("AETHER CUSTODY SERVICES", 16),
        ("Investment Holding Statement", 13),
        ("", 10),
        ("Custodian: Aether Custody Services", 10),
        ("Account Number: ACC-998877", 10),
        ("Account Title: Morgan Family Trust", 10),
        ("Statement Date: 15/07/2026", 10),
        ("Currency: USD", 10),
        ("", 10),
        ("Scheme Name          | Holding Qty | NAV     | Current Value | ISIN", 10),
        ("Vanguard Total Stock | 120.5000    | 245.10  | 29534.55      | US9229087690", 10),
        ("Apple Inc            | 50.0000     | 214.32  | 10716.00      | US0378331005", 10),
        ("Microsoft Corp       | 25.0000     | 448.10  | 11202.50      | US5949181045", 10),
        ("Cash Sweep           | 5000.0000   | 1.00    | 5000.00       |", 10),
    ]

    y = 48
    for text, size in lines:
        if text:
            page.insert_text((40, y), text, fontsize=size, fontname="helv")
        y += 20 if size >= 13 else 16

    pdf_bytes = doc.tobytes()
    doc.close()

    storage.write_bytes(key, pdf_bytes)
    logger.info("STEP | Sample PDF written via storage | key=%s bytes=%s", key, len(pdf_bytes))
    return key
