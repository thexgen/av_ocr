"""
Pipeline export façade.

Debug artifacts stay here; final business exports live in poc.export
(canonical JSON + TRANSACTION/CASH CSVs). Holdings CSV is no longer produced.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from poc.config import OUTPUT_PREFIX
from poc.export.canonical import CanonicalTransaction
from poc.export.persist import date_stamp, persist_canonical_and_csvs
from poc.export.schemas import DOCUMENT_TYPE_BANK_STATEMENT
from poc.interfaces.storage import StorageService
from poc.pipeline.mapping_dictionary import build_mapping_analysis

logger = logging.getLogger("holding_engine")

# Re-export for callers that imported date_stamp from this module
__all__ = [
    "date_stamp",
    "persist_extraction_debug_outputs",
    "persist_outputs",
]


def persist_extraction_debug_outputs(
    storage: StorageService,
    *,
    job_id: str,
    metadata: dict[str, Any],
    headers: list[str],
    rows: list[dict[str, Any]],
    raw_text: str,
    document_type: str,
    page_count: int,
) -> dict[str, str]:
    """Persist extraction and dictionary coverage before mapping alters anything."""
    base = f"{OUTPUT_PREFIX}/{job_id}"
    extracted_key = f"{base}/actual_extracted_output.json"
    analysis_key = f"{base}/mapping_analysis.json"
    extracted_payload = {
        "metadata": metadata,
        "headers": headers,
        "rows": rows,
        "raw_text": raw_text,
        "document_type": document_type,
        "page_count": page_count,
    }

    storage.write_text(
        extracted_key, json.dumps(extracted_payload, indent=2, ensure_ascii=False)
    )
    storage.write_text(
        analysis_key,
        json.dumps(build_mapping_analysis(headers), indent=2, ensure_ascii=False),
    )
    logger.info(
        "Persisted extraction debugging outputs | extracted=%s analysis=%s",
        extracted_key,
        analysis_key,
    )
    return {
        "actual_extracted_output_key": extracted_key,
        "mapping_analysis_key": analysis_key,
    }


def persist_outputs(
    storage: StorageService,
    *,
    job_id: str,
    transactions: list[CanonicalTransaction],
    mapping_response: dict[str, Any],
    extraction_info: dict[str, Any],
    document_type: str = DOCUMENT_TYPE_BANK_STATEMENT,
    asof_hint: str | None = None,
) -> dict[str, str]:
    """
    Persist canonical_transactions.json then TRANSACTION_*.csv and CASH_*.csv.
    Generators read only from the canonical transaction list.
    """
    return persist_canonical_and_csvs(
        storage,
        job_id=job_id,
        transactions=transactions,
        extraction_info=extraction_info,
        mapping_response=mapping_response,
        document_type=document_type,
        asof_hint=asof_hint,
    )
