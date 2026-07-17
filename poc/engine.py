from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from poc.config import OUTPUT_PREFIX, UPLOADS_PREFIX, cfg
from poc.exceptions import UnsupportedDocumentError
from poc.interfaces.storage import StorageService
from poc.job.history_store import HistoryStore, save_validation_report
from poc.job.job_manager import JobManager
from poc.job.models import UploadHistory, utc_now_iso
from poc.logging_setup import bind_job, set_stage

logger = logging.getLogger("holding_engine")


class ProcessingEngine:
    """
    Production local processing engine.

    Owns Job ID creation, upload registration, history, and pipeline kickoff.
    Storage backend remains swappable via StorageService.
    """

    def __init__(self, storage: StorageService) -> None:
        self.storage = storage
        self.job_manager = JobManager(storage)
        self.history_store = HistoryStore(storage)

    def register_upload(
        self,
        *,
        source_key: str | None = None,
        source_bytes: bytes | None = None,
        original_file_name: str,
        user_id: str | None = None,
        initial_status: str = "PROCESSING",
    ) -> UploadHistory:
        """
        Create Job ID, persist file via StorageService, write upload history.
        Does NOT run the pipeline (caller may process sync or in background).
        """
        job_id = self.job_manager.create_job_id()
        bind_job(job_id)
        set_stage("UPLOAD")

        user_id = user_id or str(
            cfg("placeholders", "default_user_id", default="USER_LOCAL_001")
        )
        document_type = str(
            cfg("processing", "document_type", default="Holding Statement")
        )

        ext = Path(original_file_name).suffix.lower()
        supported = [
            str(x).lower()
            for x in (cfg("supported_extensions", default=[".pdf"]) or [".pdf"])
        ]
        if ext not in supported:
            history = self._build_history(
                job_id=job_id,
                user_id=user_id,
                original_file_name=original_file_name,
                stored_file_name="",
                document_type=document_type,
                file_type=ext or "unknown",
                file_size=0,
                storage_location="",
                status="FAILED",
            )
            history.error_code = "UNSUPPORTED_DOCUMENT"
            history.error_message = (
                f"Unsupported extension '{ext}'. Allowed: {supported}"
            )
            self.history_store.save(history)
            from poc.pipeline.validation import build_validation_report

            report = build_validation_report(
                job_id=job_id,
                status="FAILED",
                total_rows=0,
                valid_rows=0,
                error_rows=0,
                warnings=[history.error_message],
                error_code=history.error_code,
                error_message=history.error_message,
                processing_seconds=0.0,
            )
            save_validation_report(self.storage, report)
            raise UnsupportedDocumentError(history.error_message)

        if source_bytes is None:
            if not source_key or not self.storage.exists(source_key):
                raise FileNotFoundError(f"Source not found: {source_key}")
            source_bytes = self.storage.read_bytes(source_key)

        stored_file_name = f"{job_id}_{Path(original_file_name).name}"
        storage_location = f"{UPLOADS_PREFIX}/{job_id}/{stored_file_name}"
        self.storage.write_bytes(storage_location, source_bytes)
        logger.info("Upload stored | key=%s bytes=%s", storage_location, len(source_bytes))

        history = self._build_history(
            job_id=job_id,
            user_id=user_id,
            original_file_name=original_file_name,
            stored_file_name=stored_file_name,
            document_type=document_type,
            file_type=ext,
            file_size=len(source_bytes),
            storage_location=storage_location,
            status=initial_status,
        )
        self.history_store.save(history)
        return history

    def process_job(self, job_id: str, *, force_ocr: bool = False) -> dict[str, Any]:
        """Run the existing pipeline for a registered job."""
        history = self.history_store.get(job_id)
        if history is None:
            raise FileNotFoundError(f"Unknown job_id: {job_id}")

        from poc.pipeline.runner import run_pipeline

        return run_pipeline(
            self.storage,
            history,
            self.history_store,
            force_ocr=force_ocr,
        )

    def submit_and_process(
        self,
        *,
        source_key: str | None = None,
        source_bytes: bytes | None = None,
        original_file_name: str,
        user_id: str | None = None,
        force_ocr: bool = False,
    ) -> dict:
        """CLI/sync path: register upload then process immediately."""
        history = self.register_upload(
            source_key=source_key,
            source_bytes=source_bytes,
            original_file_name=original_file_name,
            user_id=user_id,
            initial_status="QUEUED",
        )
        return self.process_job(history.job_id, force_ocr=force_ocr)

    def get_job(self, job_id: str) -> dict[str, Any] | None:
        """
        Job status payload for API: status, validation summary, artifact paths.
        """
        history = self.history_store.get(job_id)
        if history is None:
            return None

        validation_summary: dict[str, Any] | None = None
        report_key = f"{OUTPUT_PREFIX}/{job_id}/validation_report.json"
        if self.storage.exists(report_key):
            try:
                validation_summary = json.loads(self.storage.read_text(report_key))
            except Exception:  # noqa: BLE001
                validation_summary = None

        csv_path, json_path = self._find_artifact_paths(job_id)

        duration = history.processing_duration_ms
        duration_sec = None
        if duration is not None:
            duration_sec = round(duration / 1000.0, 1)

        return {
            "job_id": job_id,
            "status": history.processing_status,
            "validation_summary": validation_summary,
            "csv_path": csv_path,
            "json_path": json_path,
            "processing_duration_ms": duration,
            "processing_duration": (
                f"{duration_sec} sec" if duration_sec is not None else None
            ),
            "original_file_name": history.original_file_name,
            "error_code": history.error_code,
            "error_message": history.error_message,
        }

    def _find_artifact_paths(self, job_id: str) -> tuple[str | None, str | None]:
        prefix = f"{OUTPUT_PREFIX}/{job_id}/"
        csv_path = None
        json_path = None
        try:
            for key in self.storage.list_keys(prefix):
                name = key.rsplit("/", 1)[-1]
                if name.startswith("holding_") and name.endswith(".csv"):
                    csv_path = key
                elif name.startswith("holding_") and name.endswith(".json"):
                    json_path = key
        except Exception:  # noqa: BLE001
            pass
        return csv_path, json_path

    def _build_history(
        self,
        *,
        job_id: str,
        user_id: str,
        original_file_name: str,
        stored_file_name: str,
        document_type: str,
        file_type: str,
        file_size: int,
        storage_location: str,
        status: str,
    ) -> UploadHistory:
        return UploadHistory(
            job_id=job_id,
            user_id=user_id,
            original_file_name=original_file_name,
            stored_file_name=stored_file_name,
            document_type=document_type,
            file_type=file_type,
            file_size=file_size,
            processing_status=status,
            storage_location=storage_location,
            created_at=utc_now_iso(),
        )
