from __future__ import annotations

import logging
from pathlib import Path
from typing import BinaryIO

from poc.config import POC_ROOT
from poc.interfaces.storage import StorageService

logger = logging.getLogger("holding_engine")


class LocalStorageService(StorageService):
    """
    Local filesystem storage.

    Keys are relative paths under `root` (default: poc/).
    Example:
      sample_data/foo.pdf  ->  <root>/sample_data/foo.pdf
      output/holding.csv   ->  <root>/output/holding.csv

    Replace with an S3-backed StorageService later without changing
    pipeline/business logic — only the composition root (main) changes.
    """

    def __init__(self, root: Path | None = None) -> None:
        self.root = (root or POC_ROOT).resolve()
        logger.info("STEP | Storage backend=local root=%s", self.root)

    def _resolve(self, key: str) -> Path:
        normalized = key.replace("\\", "/").lstrip("/")
        path = (self.root / normalized).resolve()
        # Prevent path traversal outside root
        if not str(path).startswith(str(self.root)):
            raise ValueError(f"Invalid storage key (path escape): {key}")
        return path

    def read_bytes(self, key: str) -> bytes:
        path = self._resolve(key)
        logger.info("STEP | storage.read_bytes key=%s", key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key not found: {key} ({path})")
        return path.read_bytes()

    def write_bytes(self, key: str, data: bytes) -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        logger.info("STEP | storage.write_bytes key=%s bytes=%s", key, len(data))
        return key

    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        path = self._resolve(key)
        logger.info("STEP | storage.read_text key=%s", key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key not found: {key} ({path})")
        return path.read_text(encoding=encoding)

    def write_text(self, key: str, text: str, encoding: str = "utf-8") -> str:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding=encoding)
        logger.info("STEP | storage.write_text key=%s chars=%s", key, len(text))
        return key

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def open_read(self, key: str) -> BinaryIO:
        path = self._resolve(key)
        logger.info("STEP | storage.open_read key=%s", key)
        if not path.exists():
            raise FileNotFoundError(f"Storage key not found: {key} ({path})")
        return path.open("rb")

    def list_keys(self, prefix: str = "") -> list[str]:
        normalized = prefix.replace("\\", "/").lstrip("/")
        base = self._resolve(normalized) if normalized else self.root
        if not base.exists():
            return []
        keys: list[str] = []
        for path in base.rglob("*"):
            if path.is_file():
                rel = path.relative_to(self.root).as_posix()
                keys.append(rel)
        keys.sort()
        logger.info("STEP | storage.list_keys prefix=%s count=%s", prefix, len(keys))
        return keys


def get_storage_service() -> StorageService:
    """
    Composition helper.

    Today: LocalStorageService.
    Later: return S3StorageService(...) based on env/config —
    pipeline code stays unchanged.
    """
    return LocalStorageService()
