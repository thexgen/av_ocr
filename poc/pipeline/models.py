from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExtractionResult:
    pdf_type: str  # "text" | "scanned"
    extractor: str
    metadata: dict[str, Any] = field(default_factory=dict)
    headers: list[str] = field(default_factory=list)
    rows: list[dict[str, Any]] = field(default_factory=list)
    raw_text: str = ""
    raw_text_preview: str = ""

    @property
    def sample_rows(self) -> list[dict[str, Any]]:
        return self.rows[:2]
