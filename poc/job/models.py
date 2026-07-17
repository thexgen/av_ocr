from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


@dataclass
class UploadHistory:
    job_id: str
    user_id: str
    original_file_name: str
    stored_file_name: str
    document_type: str
    file_type: str
    file_size: int
    processing_status: str
    processing_start_time: str | None = None
    processing_end_time: str | None = None
    processing_duration_ms: int | None = None
    total_pages: int | None = None
    total_rows: int | None = None
    valid_rows: int | None = None
    error_rows: int | None = None
    ocr_used: bool = False
    llm_used: bool = False
    storage_location: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    error_code: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UploadHistory:
        known = {f.name for f in cls.__dataclass_fields__.values()}  # type: ignore[attr-defined]
        return cls(**{k: v for k, v in data.items() if k in known})


@dataclass
class ValidationReport:
    job_id: str
    status: str
    processing_time: str
    total_rows: int
    valid_rows: int
    error_rows: int
    warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    error_message: str | None = None
    stages: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
