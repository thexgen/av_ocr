"""Run investment-vehicle / bank-cash import with chat-friendly progress steps."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any, Callable

from backend.db.mutualfund_repository import insert_mf_rows_into_temp
from backend.db.vehicle_staging import insert_vehicle_rows
from backend.vehicle.excel_parse import (
    parse_vehicle_excel,
    peek_vehicle_type,
    row_to_mf_parsed,
    row_to_staging_dict,
)

logger = logging.getLogger("jessy.vehicle")

ProgressCb = Callable[[dict[str, Any]], None]

_VEHICLE_LABELS = {
    "mutual-fund": "Mutual Fund",
    "fixed-income": "Fixed Income",
    "direct-equity": "Direct Equity",
    "bank-cash": "Bank Cash",
}

_REDIRECT = {
    "mutual-fund": "/transactions/mutual-fund?tab=upload",
    "fixed-income": "/transactions/fixed-income?tab=upload",
    "direct-equity": "/transactions/direct-equity?tab=upload",
    "bank-cash": "/transactions/bank-cash?tab=upload",
}


def _step(
    emit: ProgressCb | None,
    steps: list[dict[str, Any]],
    *,
    key: str,
    label: str,
    status: str = "done",
    detail: str | None = None,
) -> None:
    item: dict[str, Any] = {"key": key, "label": label, "status": status}
    if detail:
        item["detail"] = detail
    steps.append(item)
    if emit:
        emit(item)


def _finish(
    *,
    status: str,
    job_id: str | None,
    vehicle_type: str | None,
    file_name: str,
    rows_staged: int,
    steps: list[dict[str, Any]],
    message: str,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    redirect = None
    if vehicle_type and vehicle_type in _REDIRECT:
        redirect = _REDIRECT[vehicle_type]
        if job_id:
            sep = "&" if "?" in redirect else "?"
            redirect = f"{redirect}{sep}job={job_id}"
    payload = {
        "status": status,
        "job_id": job_id,
        "vehicle_type": vehicle_type,
        "file_name": file_name,
        "rows_staged": rows_staged,
        "steps": steps,
        "message": message,
        "redirect_to": redirect,
    }
    if extra:
        payload.update(extra)
    return payload


def process_bank_cash_pdf(
    *,
    content: bytes,
    filename: str,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    """Register bank-cash PDF job (pipeline runs in background by caller)."""
    from backend.api.deps import get_engine
    from backend.exceptions import ProcessingError, UnsupportedDocumentError

    steps: list[dict[str, Any]] = []
    original = Path(filename).name or "statement.pdf"

    _step(on_progress, steps, key="receive", label="File received", detail=original)
    _step(
        on_progress,
        steps,
        key="detect",
        label="Identified as Bank Cash PDF",
        detail="Routing to bank statement pipeline",
    )

    try:
        engine = get_engine()
        history = engine.register_upload(
            source_bytes=content,
            original_file_name=original,
            initial_status="PROCESSING",
        )
    except UnsupportedDocumentError as exc:
        _step(on_progress, steps, key="done", label=str(exc.message), status="error")
        return _finish(
            status="failed",
            job_id=None,
            vehicle_type="bank-cash",
            file_name=original,
            rows_staged=0,
            steps=steps,
            message=exc.message,
        )
    except ProcessingError as exc:
        _step(on_progress, steps, key="done", label=str(exc.message), status="error")
        return _finish(
            status="failed",
            job_id=None,
            vehicle_type="bank-cash",
            file_name=original,
            rows_staged=0,
            steps=steps,
            message=exc.message,
        )

    _step(
        on_progress,
        steps,
        key="extract",
        label="Text extraction started",
        detail="Processing in background — opening Bank Cash Upload",
    )
    _step(
        on_progress,
        steps,
        key="done",
        label="Job queued",
        detail=f"Job {history.job_id}",
    )

    return _finish(
        status="processing",
        job_id=history.job_id,
        vehicle_type="bank-cash",
        file_name=original,
        rows_staged=0,
        steps=steps,
        message=(
            f"Bank Cash PDF accepted (job {history.job_id}). "
            "Opening Bank Cash Upload to show progress and temp transactions."
        ),
        extra={"needs_background_process": True},
    )


def process_vehicle_attachment(
    *,
    content: bytes,
    filename: str,
    expect_vehicle: str | None = None,
    on_progress: ProgressCb | None = None,
) -> dict[str, Any]:
    """Detect file, parse Excel vehicles or register bank PDF, stage rows."""
    steps: list[dict[str, Any]] = []
    original = Path(filename).name or "upload.bin"
    suffix = Path(original).suffix.lower()

    _step(on_progress, steps, key="receive", label="File received", detail=original)

    if suffix == ".pdf":
        return process_bank_cash_pdf(
            content=content, filename=original, on_progress=on_progress
        )

    if suffix not in {".xls", ".xlsx"}:
        _step(
            on_progress,
            steps,
            key="detect",
            label="Unsupported file type",
            status="error",
            detail="Use PDF for Bank Cash, or Excel for Mutual Fund / Fixed Income / Direct Equity",
        )
        return _finish(
            status="acknowledged",
            job_id=None,
            vehicle_type=None,
            file_name=original,
            rows_staged=0,
            steps=steps,
            message=f"Received {original}. Unsupported type for import.",
        )

    _step(
        on_progress,
        steps,
        key="detect",
        label="Detecting file type",
        status="running",
    )
    vehicle, sheet_name, _headers = peek_vehicle_type(content, original)
    if expect_vehicle and not vehicle:
        vehicle = expect_vehicle
    label = _VEHICLE_LABELS.get(vehicle or "", "Unknown")
    steps[-1] = {
        "key": "detect",
        "label": f"Identified as {label} file" if vehicle else "Could not identify file type",
        "status": "done" if vehicle else "error",
        "detail": f"Sheet: {sheet_name}" if sheet_name else None,
    }
    if on_progress:
        on_progress(steps[-1])

    if vehicle not in {"mutual-fund", "fixed-income", "direct-equity"}:
        msg = "Could not identify this Excel as MF / Fixed Income / Direct Equity."
        _step(on_progress, steps, key="done", label=msg, status="error")
        return _finish(
            status="unsupported",
            job_id=None,
            vehicle_type=vehicle,
            file_name=original,
            rows_staged=0,
            steps=steps,
            message=msg,
        )

    _step(
        on_progress,
        steps,
        key="extract",
        label="Extracting rows from Excel",
        status="running",
    )
    try:
        parsed = parse_vehicle_excel(content, original, expect=vehicle)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Vehicle parse failed | file=%s", original)
        steps[-1] = {
            "key": "extract",
            "label": "Text / row extraction failed",
            "status": "error",
            "detail": str(exc),
        }
        if on_progress:
            on_progress(steps[-1])
        return _finish(
            status="failed",
            job_id=None,
            vehicle_type=vehicle,
            file_name=original,
            rows_staged=0,
            steps=steps,
            message=f"Failed to extract rows: {exc}",
        )

    steps[-1] = {
        "key": "extract",
        "label": "Text extracting done",
        "status": "done",
        "detail": f"{len(parsed.rows)} data row(s) from sheet {parsed.sheet_name}",
    }
    if on_progress:
        on_progress(steps[-1])

    prefix = {"mutual-fund": "MF", "fixed-income": "FI", "direct-equity": "DE"}[vehicle]
    job_id = f"{prefix}_{uuid.uuid4().hex[:12].upper()}"

    _step(
        on_progress,
        steps,
        key="validate",
        label="Validating mandatory fields",
        detail=(
            f"{sum(1 for r in parsed.rows if not r.iserror)} clean / "
            f"{sum(1 for r in parsed.rows if r.iserror)} need review"
        ),
    )

    _step(
        on_progress,
        steps,
        key="stage",
        label="Staging temp transactions",
        status="running",
    )
    try:
        if vehicle == "mutual-fund":
            summary = insert_mf_rows_into_temp(
                job_id=job_id,
                rows=[row_to_mf_parsed(r) for r in parsed.rows],
                filename=original,
            )
        else:
            summary = insert_vehicle_rows(
                vehicle=vehicle,
                job_id=job_id,
                rows=[row_to_staging_dict(r) for r in parsed.rows],
                filename=original,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception("Vehicle stage failed | job=%s", job_id)
        steps[-1] = {
            "key": "stage",
            "label": "Database staging failed",
            "status": "error",
            "detail": str(exc),
        }
        if on_progress:
            on_progress(steps[-1])
        return _finish(
            status="failed",
            job_id=job_id,
            vehicle_type=vehicle,
            file_name=original,
            rows_staged=0,
            steps=steps,
            message=f"Failed to store data: {exc}",
        )

    table_name = {
        "mutual-fund": "mutualfundtemp",
        "fixed-income": "fixedincometemp",
        "direct-equity": "directequitytemp",
    }[vehicle]
    steps[-1] = {
        "key": "stage",
        "label": "Temp transactions staged",
        "status": "done",
        "detail": (
            f"{summary['inserted']} row(s) -> {table_name} "
            f"({summary['clean_rows']} clean, {summary['error_rows']} errors)"
        ),
    }
    if on_progress:
        on_progress(steps[-1])

    if summary["inserted"] == 0:
        done_msg = (
            f"{label} template recognized, but the file has no data rows "
            "(header only). Add transaction rows and re-upload."
        )
        status = "empty"
    else:
        done_msg = (
            f"{label} import complete — {summary['inserted']} temp row(s) stored. "
            f"Opening {label} Upload to review."
        )
        status = "success"

    _step(on_progress, steps, key="done", label="Completed", detail=done_msg)

    return _finish(
        status=status,
        job_id=job_id,
        vehicle_type=vehicle,
        file_name=original,
        rows_staged=summary["inserted"],
        steps=steps,
        message=done_msg,
        extra={
            "clean_rows": summary["clean_rows"],
            "error_rows": summary["error_rows"],
            "sheet_name": parsed.sheet_name,
        },
    )
