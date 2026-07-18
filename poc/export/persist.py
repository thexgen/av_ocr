"""
Persist canonical_transactions.json then run registered CSV generators.

Both TRANSACTION_*.csv and CASH_*.csv are produced only from the canonical list.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from poc.config import OUTPUT_PREFIX
from poc.export.canonical import CanonicalTransaction, canonical_list_to_dicts
from poc.export.generators import CsvGenerator, default_bank_statement_generators
from poc.export.schemas import DOCUMENT_TYPE_BANK_STATEMENT
from poc.interfaces.storage import StorageService

logger = logging.getLogger("holding_engine")


def date_stamp(asof_hint: str | None = None) -> str:
    """Prefer statement date as YYYYMMDD; else today."""
    if asof_hint:
        text = asof_hint.strip()
        # "01 Sep 2023" / "01-Sep-2023"
        months = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        parts_sp = text.replace("-", " ").split()
        if len(parts_sp) == 3 and parts_sp[1][:3].lower() in months and parts_sp[2].isdigit():
            d, mon, y = parts_sp[0], parts_sp[1][:3].lower(), parts_sp[2]
            if d.isdigit():
                return f"{y}{months[mon]:02d}{int(d):02d}"

        for sep in ("-", "/", "."):
            parts = text.split(sep)
            if len(parts) == 3 and len(parts[0]) == 4 and parts[0].isdigit():
                y, m, d = parts
                if len(m) <= 2 and len(d) <= 2 and m.isdigit() and d.isdigit():
                    return f"{y}{int(m):02d}{int(d):02d}"
        for sep in ("/", "-", "."):
            parts = text.split(sep)
            if len(parts) == 3 and len(parts[2]) == 4 and parts[2].isdigit():
                d, m, y = parts
                if d.isdigit() and m.isdigit():
                    return f"{y}{int(m):02d}{int(d):02d}"
    return datetime.now().strftime("%Y%m%d")


def build_canonical_payload(
    *,
    job_id: str,
    transactions: list[CanonicalTransaction],
    extraction_info: dict[str, Any],
    mapping_response: dict[str, Any],
    document_type: str,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "document_type": document_type,
        "record_count": len(transactions),
        "extraction": extraction_info,
        "mapping": {
            k: v for k, v in mapping_response.items() if not str(k).startswith("_")
        },
        "mapper": mapping_response.get("_mapper"),
        "transactions": canonical_list_to_dicts(transactions),
    }


def persist_canonical_and_csvs(
    storage: StorageService,
    *,
    job_id: str,
    transactions: list[CanonicalTransaction],
    extraction_info: dict[str, Any],
    mapping_response: dict[str, Any],
    document_type: str = DOCUMENT_TYPE_BANK_STATEMENT,
    asof_hint: str | None = None,
    generators: list[CsvGenerator] | None = None,
) -> dict[str, str]:
    """
    1) Write canonical_transactions.json
    2) Generate each CSV solely from that canonical list
    """
    stamp = date_stamp(asof_hint)
    base = f"{OUTPUT_PREFIX}/{job_id}"
    canonical_key = f"{base}/canonical_transactions.json"

    payload = build_canonical_payload(
        job_id=job_id,
        transactions=transactions,
        extraction_info=extraction_info,
        mapping_response=mapping_response,
        document_type=document_type,
    )
    storage.write_text(
        canonical_key, json.dumps(payload, indent=2, ensure_ascii=False)
    )
    logger.info("Persisted canonical transactions | %s | rows=%s", canonical_key, len(transactions))

    # Reload-from-canonical contract: generators receive the in-memory list that
    # was just serialized (same content as canonical_transactions.json).
    gens = generators if generators is not None else default_bank_statement_generators()
    keys: dict[str, str] = {
        "canonical_key": canonical_key,
        "output_prefix": base,
    }

    for gen in gens:
        csv_name = gen.filename(stamp)
        csv_key = f"{base}/{csv_name}"
        csv_text = gen.build_csv(transactions)
        storage.write_text(csv_key, csv_text)
        keys[f"{gen.name}_csv_key"] = csv_key
        logger.info("Persisted %s | %s | rows=%s", gen.name, csv_key, len(transactions))

    return keys
