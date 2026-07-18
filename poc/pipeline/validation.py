from __future__ import annotations

import logging
import re
from typing import Any

from poc.config import cfg
from poc.job.models import ValidationReport
from poc.logging_setup import format_processing_time, job_elapsed_seconds
from poc.pipeline.statement_parse import STANDARD_BANK_HEADERS, count_date_led_lines

logger = logging.getLogger("holding_engine")

_AMOUNT_HEADER_TOKENS = (
    "withdrawal",
    "deposit",
    "debit",
    "credit",
    "balance",
    "amount",
    "debit/credit",
)


def _headers_look_like_data(headers: list[str]) -> bool:
    """True when headers appear to be data cells promoted to column names."""
    if not headers:
        return True
    dataish = 0
    for h in headers:
        c = (h or "").strip()
        if not c:
            continue
        if re.match(r"^col_\d+$", c, re.I):
            dataish += 1
            continue
        if re.match(r"^[\d,.\-+/]+$", c.replace(" ", "")):
            dataish += 1
            continue
        if re.search(r"\d{1,3}(?:,\d{2,3})+\.\d{2}", c):
            dataish += 1
            continue
        if re.search(r"(?:NEFT|IMPS|RTGS|INF/)", c, re.I) and re.search(r"\d{5,}", c):
            dataish += 1
            continue
        if re.match(r"^[A-Z]\d{3,}", c) and sum(ch.isdigit() for ch in c) >= 3:
            dataish += 1
            continue
    nonempty = [h for h in headers if (h or "").strip()]
    return bool(nonempty) and dataish >= max(2, (len(nonempty) + 1) // 2)


def _headers_look_like_warning_prose(headers: list[str]) -> bool:
    joined = " ".join(headers).lower()
    probes = (
        "minimum payment",
        "if you make",
        "estimated total",
        "you will pay off",
        "additional charges using this card",
        "important notices",
        "error resolution",
    )
    return any(p in joined for p in probes) or any(len(h or "") > 80 for h in headers)


def headers_are_synthetic(
    headers: list[str],
    *,
    bank_parser_headers: bool = False,
    extract_warnings: list[str] | None = None,
) -> bool:
    """
    Synthetic = unusable schema (data-as-header, col_N, warning prose, raw dump).
    Intentional STANDARD_BANK_HEADERS from the bank parser are NOT synthetic.
    """
    if not headers:
        return True
    if headers == list(STANDARD_BANK_HEADERS) or bank_parser_headers:
        return False
    if headers == ["LineNo", "RawText"]:
        return True
    if any(re.match(r"^col_\d+$", (h or "").strip(), re.I) for h in headers):
        return True
    if _headers_look_like_data(headers):
        return True
    if _headers_look_like_warning_prose(headers):
        return True
    warnings = extract_warnings or []
    if any("raw text lines" in w.lower() for w in warnings):
        return True
    return False


def has_debit_credit_or_balance_headers(headers: list[str]) -> bool:
    joined = " ".join(h or "" for h in headers).lower()
    return any(tok in joined for tok in _AMOUNT_HEADER_TOKENS)


def assess_bank_extraction_quality(
    *,
    headers: list[str],
    rows: list[dict[str, Any]],
    raw_text: str,
    extract_warnings: list[str] | None = None,
    bank_parser_headers: bool = False,
) -> list[str]:
    """
    Hard quality gates for bank-statement structured extraction.
    Returns a list of failure reasons (empty => pass).
    """
    failures: list[str] = []
    warnings = list(extract_warnings or [])
    row_count = len(rows or [])
    date_led = count_date_led_lines(raw_text or "")

    if headers_are_synthetic(
        headers,
        bank_parser_headers=bank_parser_headers,
        extract_warnings=warnings,
    ):
        failures.append(
            "Headers are synthetic or unusable (data-as-header, placeholder, "
            "warning/legal text, or raw line dump)"
        )

    if not has_debit_credit_or_balance_headers(headers or []):
        failures.append(
            "Debit/Credit/Balance (or Amount) columns missing from extracted headers"
        )

    # Suspiciously low row count vs date-led lines visible in the PDF text
    if date_led >= 10 and row_count <= 3:
        failures.append(
            f"Row count suspiciously low ({row_count}) vs {date_led} date-led lines in text"
        )
    elif date_led >= 20 and row_count < max(5, int(date_led * 0.15)):
        failures.append(
            f"Row count suspiciously low ({row_count}) vs {date_led} date-led lines in text"
        )
    elif row_count < 2 and date_led >= 5:
        failures.append(
            f"Row count suspiciously low ({row_count}) vs {date_led} date-led lines in text"
        )

    return failures


def classify_rows(records: list[dict[str, Any]]) -> tuple[int, int, list[str]]:
    """
    Classify normalized rows as valid vs error using configured required fields.
    Returns (valid_rows, error_rows, warning_messages).
    """
    required = list(cfg("validation", "required_fields", default=[
        "SecurityDescription",
        "Quantity",
        "MarketValueLocal",
    ]) or [])
    confidence_threshold = float(cfg("processing", "confidence_threshold", default=70))

    valid = 0
    error = 0
    warnings: list[str] = []

    for i, row in enumerate(records):
        missing = [f for f in required if row.get(f) in (None, "")]
        if missing:
            error += 1
            warnings.append(f"Row {i + 1}: missing required fields {missing}")
            continue
        valid += 1

    # Confidence threshold is informational for mapper output; row-level confidence
    # is not always present — keep as config knob for future use.
    _ = confidence_threshold

    return valid, error, warnings


def build_validation_report(
    *,
    job_id: str,
    status: str,
    total_rows: int,
    valid_rows: int,
    error_rows: int,
    warnings: list[str] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    stages: list[dict[str, Any]] | None = None,
    processing_seconds: float | None = None,
) -> ValidationReport:
    seconds = processing_seconds if processing_seconds is not None else job_elapsed_seconds()
    report = ValidationReport(
        job_id=job_id,
        status=status,
        processing_time=format_processing_time(seconds),
        total_rows=total_rows,
        valid_rows=valid_rows,
        error_rows=error_rows,
        warnings=warnings or [],
        error_code=error_code,
        error_message=error_message,
        stages=stages or [],
    )
    logger.info(
        "Validation report ready | status=%s total=%s valid=%s error=%s",
        status,
        total_rows,
        valid_rows,
        error_rows,
    )
    return report
