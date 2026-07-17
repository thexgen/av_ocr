from __future__ import annotations

from functools import lru_cache

from poc.engine import ProcessingEngine
from poc.services.storage_service import get_storage_service


@lru_cache(maxsize=1)
def get_engine() -> ProcessingEngine:
    """Shared engine instance (local storage)."""
    return ProcessingEngine(get_storage_service())
