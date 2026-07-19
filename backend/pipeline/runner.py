from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from backend.config import OUTPUT_PREFIX, cfg
from backend.exceptions import (
    EmptyPDFError,
    ExtractionQualityError,
    OCRFailureError,
    ProcessingError,
    UnsupportedDocumentError,
)
from backend.interfaces.storage import StorageService
from backend.job.history_store import HistoryStore, save_validation_report
from backend.job.models import UploadHistory
from backend.logging_setup import bind_job, format_processing_time, job_elapsed_seconds, stage
from backend.db.bankcash_repository import insert_canonical_into_temp
from backend.export.canonical import build_canonical_transactions
from backend.export.schemas import DOCUMENT_TYPE_BANK_STATEMENT
from backend.pipeline.export import persist_extraction_debug_outputs, persist_outputs
from backend.pipeline.extract_ocr_pdf import extract_with_paddleocr
from backend.pipeline.extract_text_pdf import extract_with_pymupdf
from backend.pipeline.pdf_detect import detect_pdf_type
from backend.pipeline.mapping_engine import resolve_field_mapping
from backend.pipeline.validation import (
    assess_bank_extraction_quality,
    build_validation_report,
    classify_rows,
)

logger = logging.getLogger("holding_engine")


def run_pipeline(
    storage: StorageService,
    history: UploadHistory,
    history_store: HistoryStore,
    *,
    force_ocr: bool = False,
) -> dict[str, Any]:
    """
    Job-scoped, storage-agnostic pipeline.

    Never raises to the CLI for handled failures — always writes
    validation_report.json and updates upload history.
    """
    job_id = history.job_id
    input_key = history.storage_location
    bind_job(job_id)

    start_dt = datetime.now()
    history.processing_status = "PROCESSING"
    history.processing_start_time = start_dt.isoformat(timespec="seconds")
    history_store.save(history)

    stages: list[dict[str, Any]] = []
    ocr_used = False
    llm_used = False
    total_pages = 0
    canonical_rows: list[Any] = []
    keys: dict[str, str] = {}
    debug_keys: dict[str, str] = {}
    db_summary: dict[str, Any] = {}
    document_type = str(
        cfg("processing", "document_type", default=DOCUMENT_TYPE_BANK_STATEMENT)
    )

    def _mark_stage(name: str, detail: str = "ok") -> None:
        stages.append({"stage": name, "detail": detail, "at": datetime.now().isoformat(timespec="seconds")})

    try:
        with stage("VALIDATE_INPUT", logger):
            if not storage.exists(input_key):
                raise UnsupportedDocumentError(f"Input not found in storage: {input_key}")

            max_bytes = int(cfg("processing", "max_file_size_mb", default=25)) * 1024 * 1024
            pdf_bytes = storage.read_bytes(input_key)
            if history.file_size and history.file_size > max_bytes:
                from backend.exceptions import FileTooLargeError

                raise FileTooLargeError(
                    f"File size {history.file_size} exceeds max_file_size_mb"
                )
            if len(pdf_bytes) > max_bytes:
                from backend.exceptions import FileTooLargeError

                raise FileTooLargeError(
                    f"File size {len(pdf_bytes)} exceeds configured max_file_size_mb"
                )
            _mark_stage("VALIDATE_INPUT")

        with stage("DETECT", logger):
            pdf_type, stats = detect_pdf_type(pdf_bytes, source_label=input_key)
            total_pages = int(stats.get("page_count") or 0)
            if force_ocr:
                logger.warning("--force-ocr set: overriding type to scanned")
                pdf_type = "scanned"
            _mark_stage("DETECT", pdf_type)

        with stage("EXTRACT", logger):
            if pdf_type == "text":
                logger.info("Route -> PyMuPDF (text-based PDF)")
                extraction = extract_with_pymupdf(pdf_bytes, source_label=input_key)
            else:
                if not bool(cfg("processing", "ocr_enabled", default=True)):
                    raise OCRFailureError("Scanned PDF detected but OCR is disabled")
                logger.info("Route -> PaddleOCR (scanned / image PDF)")
                ocr_used = True
                try:
                    extraction = extract_with_paddleocr(pdf_bytes, source_label=input_key)
                except ProcessingError:
                    raise
                except Exception as exc:  # noqa: BLE001
                    raise OCRFailureError(f"OCR extraction failed: {exc}") from exc
            _mark_stage("EXTRACT", extraction.extractor)

        # Capture the extractor's output before dictionary lookup or mapping.
        debug_keys = persist_extraction_debug_outputs(
            storage,
            job_id=job_id,
            metadata=extraction.metadata,
            headers=extraction.headers,
            rows=extraction.rows,
            raw_text=extraction.raw_text,
            document_type=document_type,
            page_count=total_pages,
        )

        if not extraction.headers and not extraction.rows:
            raise EmptyPDFError("No content could be extracted from the document")

        extract_warnings = list(extraction.metadata.pop("_extract_warnings", []) or [])
        bank_parser_headers = bool(extraction.metadata.pop("_bank_parser_headers", False))

        quality_failures = assess_bank_extraction_quality(
            headers=extraction.headers or [],
            rows=extraction.rows or [],
            raw_text=extraction.raw_text or "",
            extract_warnings=extract_warnings,
            bank_parser_headers=bank_parser_headers,
        )
        if quality_failures:
            raise ExtractionQualityError(
                "Bank statement extraction quality check failed: "
                + "; ".join(quality_failures),
                warnings=extract_warnings + quality_failures,
            )

        with stage("MAP", logger):
            mapping_response = resolve_field_mapping(
                metadata=extraction.metadata,
                headers=extraction.headers or ["RawText"],
                sample_rows=extraction.sample_rows
                or (extraction.rows[:2] if extraction.rows else [{"RawText": extraction.raw_text_preview}]),
            )
            llm_used = bool(mapping_response.get("_llm_used"))
            field_mapping = mapping_response.get("field_mapping") or {}
            if not isinstance(field_mapping, dict):
                field_mapping = {}
            # Pipeline continues even if some/all headers stay unmapped
            if not field_mapping:
                mapping_response.setdefault("warnings", []).append(
                    "No headers mapped yet — canonical fields may remain blank"
                )
            mapping_response["document_type"] = document_type
            _mark_stage("MAP", mapping_response.get("_mapper", "unknown"))

        with stage("CANONICALIZE", logger):
            canonical_rows = build_canonical_transactions(
                rows=extraction.rows,
                field_mapping=field_mapping,
                metadata=extraction.metadata,
                mapping_metadata=mapping_response.get("metadata") or {},
                document_type=document_type,
            )
            _mark_stage("CANONICALIZE", f"rows={len(canonical_rows)}")

        with stage("VALIDATE_ROWS", logger):
            validation_records = [r.to_validation_record() for r in canonical_rows]
            valid_rows, error_rows, row_warnings = classify_rows(validation_records)
            map_warnings = list(mapping_response.get("warnings") or [])
            warnings = extract_warnings + map_warnings + row_warnings
            _mark_stage("VALIDATE_ROWS", f"valid={valid_rows} error={error_rows}")

        with stage("PERSIST", logger):
            asof = (
                (mapping_response.get("metadata") or {}).get("statement_date")
                or extraction.metadata.get("statement_date")
            )
            # Prefer first trade date for filename stamp when statement_date absent
            if not asof and canonical_rows:
                asof = canonical_rows[0].trade_date or canonical_rows[0].asof_date
            extraction_info = {
                "input_key": input_key,
                "pdf_type": extraction.pdf_type,
                "extractor": extraction.extractor,
                "detection_stats": stats,
                "headers": extraction.headers,
                "row_count": len(extraction.rows),
                "metadata": extraction.metadata,
            }
            keys = persist_outputs(
                storage=storage,
                job_id=job_id,
                transactions=canonical_rows,
                mapping_response=mapping_response,
                extraction_info=extraction_info,
                document_type=document_type,
                asof_hint=asof,
            )
            _mark_stage("PERSIST")

        with stage("DB_STAGE", logger):
            db_summary = insert_canonical_into_temp(
                job_id=job_id,
                transactions=canonical_rows,
                filename=history.original_file_name,
            )
            warnings.append(
                f"Staged {db_summary.get('inserted', 0)} row(s) into bankcashtemp "
                f"(clean={db_summary.get('clean_rows', 0)}, "
                f"error={db_summary.get('error_rows', 0)})"
            )
            _mark_stage(
                "DB_STAGE",
                f"inserted={db_summary.get('inserted', 0)} "
                f"error={db_summary.get('error_rows', 0)}",
            )

        # Prefer DB staging validation counts when available
        db_error_rows = int(db_summary.get("error_rows") or 0)
        db_clean_rows = int(db_summary.get("clean_rows") or 0)
        if db_summary.get("inserted"):
            error_rows = db_error_rows
            valid_rows = db_clean_rows

        status = "SUCCESS" if error_rows == 0 else "SUCCESS_WITH_WARNINGS"
        elapsed = job_elapsed_seconds()
        report = build_validation_report(
            job_id=job_id,
            status=status,
            total_rows=len(canonical_rows),
            valid_rows=valid_rows,
            error_rows=error_rows,
            warnings=warnings,
            stages=stages,
            processing_seconds=elapsed,
        )
        report_key = save_validation_report(storage, report)

        _finalize_history(
            history_store,
            history,
            status=status,
            start_dt=start_dt,
            total_pages=total_pages,
            total_rows=len(canonical_rows),
            valid_rows=valid_rows,
            error_rows=error_rows,
            ocr_used=ocr_used,
            llm_used=llm_used,
        )

        logger.info(
            "JOB COMPLETE | status=%s time=%s canonical=%s txn_csv=%s cash_csv=%s report=%s",
            status,
            format_processing_time(elapsed),
            keys.get("canonical_key"),
            keys.get("transaction_csv_key"),
            keys.get("cash_csv_key"),
            report_key,
        )
        return {
            "job_id": job_id,
            "status": status,
            "canonical_key": keys.get("canonical_key"),
            "transaction_csv_key": keys.get("transaction_csv_key"),
            "cash_csv_key": keys.get("cash_csv_key"),
            "json_key": keys.get("canonical_key"),
            "csv_key": keys.get("transaction_csv_key"),
            "actual_extracted_output_key": debug_keys.get("actual_extracted_output_key"),
            "mapping_analysis_key": debug_keys.get("mapping_analysis_key"),
            "validation_report_key": report_key,
            "records": len(canonical_rows),
            "valid_rows": valid_rows,
            "error_rows": error_rows,
            "ocr_used": ocr_used,
            "llm_used": llm_used,
            "document_type": document_type,
            "db_staged": db_summary.get("inserted", 0),
            "db_error_rows": db_summary.get("error_rows", 0),
            "db_clean_rows": db_summary.get("clean_rows", 0),
            "entity_id": db_summary.get("entity_id"),
            "entity_name": db_summary.get("entity_name"),
        }

    except ProcessingError as exc:
        return _fail(
            storage=storage,
            history_store=history_store,
            history=history,
            start_dt=start_dt,
            stages=stages,
            exc=exc,
            total_pages=total_pages,
            ocr_used=ocr_used,
            llm_used=llm_used,
            total_rows=len(canonical_rows),
        )
    except Exception as exc:  # noqa: BLE001
        # Unexpected errors still produce a validation report — never crash silently
        wrapped = ProcessingError(f"Unexpected processing failure: {exc}")
        logger.exception("Unhandled error in pipeline")
        return _fail(
            storage=storage,
            history_store=history_store,
            history=history,
            start_dt=start_dt,
            stages=stages,
            exc=wrapped,
            total_pages=total_pages,
            ocr_used=ocr_used,
            llm_used=llm_used,
            total_rows=len(canonical_rows),
        )


def _finalize_history(
    history_store: HistoryStore,
    history: UploadHistory,
    *,
    status: str,
    start_dt: datetime,
    total_pages: int,
    total_rows: int,
    valid_rows: int,
    error_rows: int,
    ocr_used: bool,
    llm_used: bool,
    error_code: str | None = None,
    error_message: str | None = None,
) -> None:
    end_dt = datetime.now()
    duration_ms = int((end_dt - start_dt).total_seconds() * 1000)
    history.processing_status = status
    history.processing_end_time = end_dt.isoformat(timespec="seconds")
    history.processing_duration_ms = duration_ms
    history.total_pages = total_pages
    history.total_rows = total_rows
    history.valid_rows = valid_rows
    history.error_rows = error_rows
    history.ocr_used = ocr_used
    history.llm_used = llm_used
    history.error_code = error_code
    history.error_message = error_message
    history_store.save(history)


def _fail(
    *,
    storage: StorageService,
    history_store: HistoryStore,
    history: UploadHistory,
    start_dt: datetime,
    stages: list[dict[str, Any]],
    exc: ProcessingError,
    total_pages: int,
    ocr_used: bool,
    llm_used: bool,
    total_rows: int,
) -> dict[str, Any]:
    job_id = history.job_id
    elapsed = job_elapsed_seconds()
    stages.append(
        {
            "stage": "FAILED",
            "detail": exc.code,
            "at": datetime.now().isoformat(timespec="seconds"),
        }
    )
    report = build_validation_report(
        job_id=job_id,
        status="FAILED",
        total_rows=total_rows,
        valid_rows=0,
        error_rows=total_rows,
        warnings=list(exc.warnings) + [exc.message],
        error_code=exc.code,
        error_message=exc.message,
        stages=stages,
        processing_seconds=elapsed,
    )
    report_key = save_validation_report(storage, report)
    _finalize_history(
        history_store,
        history,
        status="FAILED",
        start_dt=start_dt,
        total_pages=total_pages,
        total_rows=total_rows,
        valid_rows=0,
        error_rows=total_rows,
        ocr_used=ocr_used,
        llm_used=llm_used,
        error_code=exc.code,
        error_message=exc.message,
    )
    logger.error(
        "JOB FAILED | code=%s message=%s report=%s time=%s",
        exc.code,
        exc.message,
        report_key,
        format_processing_time(elapsed),
    )
    return {
        "job_id": job_id,
        "status": "FAILED",
        "error_code": exc.code,
        "error_message": exc.message,
        "validation_report_key": report_key,
        "records": total_rows,
        "valid_rows": 0,
        "error_rows": total_rows,
        "ocr_used": ocr_used,
        "llm_used": llm_used,
        "output_prefix": f"{OUTPUT_PREFIX}/{job_id}",
    }
