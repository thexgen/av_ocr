from __future__ import annotations

import logging
import re
from typing import Any

from poc.config import STANDARD_SCHEMA

logger = logging.getLogger("holding_engine")

_DEBIT_HINT = re.compile(r"withdraw|debit|\(dr\)", re.I)
_CREDIT_HINT = re.compile(r"deposit|credit|\(cr\)", re.I)


def _nonempty(value: Any) -> bool:
    return value is not None and not (isinstance(value, str) and value.strip() == "")


def _signed_market_value(row: dict[str, Any], field_mapping: dict[str, str]) -> Any:
    """
    When both Withdrawal and Deposit map to MarketValueLocal, pick the non-empty
    side and mark withdrawals as negative so cash outflows stay distinct.
    """
    debit_val = None
    credit_val = None
    for source_header, schema_field in field_mapping.items():
        if schema_field != "MarketValueLocal" or source_header not in row:
            continue
        val = row[source_header]
        if not _nonempty(val):
            continue
        if _DEBIT_HINT.search(source_header):
            debit_val = val
        elif _CREDIT_HINT.search(source_header):
            credit_val = val
    if _nonempty(debit_val) and not _nonempty(credit_val):
        s = str(debit_val).strip()
        return s if s.startswith("-") else f"-{s}"
    if _nonempty(credit_val):
        return credit_val
    if _nonempty(debit_val):
        s = str(debit_val).strip()
        return s if s.startswith("-") else f"-{s}"
    return None


def apply_mapping_to_rows(
    rows: list[dict[str, Any]],
    field_mapping: dict[str, str],
    metadata: dict[str, Any],
    mapping_metadata: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """
    Apply Qwen/local field_mapping to ALL extracted rows.
    Never invent values — unmapped schema fields are null.
    """
    logger.info("STEP | Applying field mapping to ALL %s rows", len(rows))
    logger.info("STEP | Active field_mapping: %s", field_mapping)

    mapping_metadata = mapping_metadata or {}
    normalized: list[dict[str, Any]] = []
    mv_collision = sum(1 for v in field_mapping.values() if v == "MarketValueLocal") > 1

    for idx, row in enumerate(rows):
        record: dict[str, Any] = {field: None for field in STANDARD_SCHEMA}

        # Map columns from source row using exact header keys
        for source_header, schema_field in field_mapping.items():
            if schema_field not in record:
                logger.warning(
                    "STEP | Ignoring unknown schema field from mapping: %s",
                    schema_field,
                )
                continue
            if schema_field == "MarketValueLocal" and mv_collision:
                continue
            if source_header in row:
                value = row[source_header]
                # Preserve empty as null; do not invent
                if value is None or (isinstance(value, str) and value.strip() == ""):
                    if record[schema_field] is None:
                        record[schema_field] = None
                else:
                    record[schema_field] = value

        if mv_collision:
            record["MarketValueLocal"] = _signed_market_value(row, field_mapping)

        # Propagate document-level metadata only when row field is still null
        # and metadata value is present (no invention)
        meta_pairs = [
            ("AsofDate", mapping_metadata.get("statement_date") or metadata.get("statement_date")),
            ("Custodian", mapping_metadata.get("custodian") or metadata.get("custodian")),
            ("CurrencyLocal", mapping_metadata.get("currency") or metadata.get("currency")),
            ("AccountNumber", metadata.get("account_number")),
        ]
        for schema_field, value in meta_pairs:
            if record[schema_field] is None and value not in (None, ""):
                record[schema_field] = value

        normalized.append(record)
        if idx < 3:
            logger.info("STEP | Normalized row[%s]: %s", idx, {k: v for k, v in record.items() if v is not None})

    logger.info("STEP | Normalization complete | records=%s", len(normalized))
    return normalized
