from __future__ import annotations

import json
import logging
from typing import Any

from backend.config import OUTPUT_PREFIX, cfg
from backend.interfaces.storage import StorageService
from backend.job.models import UploadHistory, ValidationReport

logger = logging.getLogger("holding_engine")


class HistoryStore:
    """
    Persist UploadHistory as local JSON via StorageService.
    Later this adapter can write to SQL without changing callers.
    """

    def __init__(self, storage: StorageService) -> None:
        self.storage = storage
        self.history_key = str(cfg("job", "history_key", default="jobs/upload_history.json"))

    def save(self, history: UploadHistory) -> str:
        # Per-job record
        job_key = f"{OUTPUT_PREFIX}/{history.job_id}/upload_history.json"
        self.storage.write_text(job_key, json.dumps(history.to_dict(), indent=2))

        # Append/upsert into global index
        records = self._load_all()
        updated = False
        for i, row in enumerate(records):
            if row.get("job_id") == history.job_id:
                records[i] = history.to_dict()
                updated = True
                break
        if not updated:
            records.append(history.to_dict())

        self.storage.write_text(self.history_key, json.dumps(records, indent=2))
        logger.info("Upload history saved | key=%s", job_key)
        return job_key

    def get(self, job_id: str) -> UploadHistory | None:
        for row in self._load_all():
            if row.get("job_id") == job_id:
                return UploadHistory.from_dict(row)
        return None

    def list_all(self) -> list[dict[str, Any]]:
        return self._load_all()

    def _load_all(self) -> list[dict[str, Any]]:
        if not self.storage.exists(self.history_key):
            return []
        try:
            data = json.loads(self.storage.read_text(self.history_key))
            return data if isinstance(data, list) else []
        except Exception:  # noqa: BLE001
            return []


def save_validation_report(storage: StorageService, report: ValidationReport) -> str:
    key = f"{OUTPUT_PREFIX}/{report.job_id}/validation_report.json"
    storage.write_text(key, json.dumps(report.to_dict(), indent=2))
    logger.info("Validation report saved | key=%s", key)
    return key
