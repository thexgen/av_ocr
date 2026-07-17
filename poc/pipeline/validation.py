from __future__ import annotations

import logging
from typing import Any

from poc.config import cfg
from poc.job.models import ValidationReport
from poc.logging_setup import format_processing_time, job_elapsed_seconds

logger = logging.getLogger("holding_engine")


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
