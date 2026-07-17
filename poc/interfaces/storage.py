from __future__ import annotations

from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageService(ABC):
    """
    Storage port for the holding pipeline.

    Keys are logical paths, e.g.:
      - sample_data/sample_holding_statement.pdf
      - output/holding_20260715.csv

    Implementations map keys to a backend (local disk today, S3 later).
    Pipeline code must not import S3/boto3 or assume local Paths.
    """

    @abstractmethod
    def read_bytes(self, key: str) -> bytes:
        """Read object bytes by key."""

    @abstractmethod
    def write_bytes(self, key: str, data: bytes) -> str:
        """
        Write bytes to key.
        Returns the logical key (or URI) that was written.
        """

    @abstractmethod
    def read_text(self, key: str, encoding: str = "utf-8") -> str:
        """Read text object by key."""

    @abstractmethod
    def write_text(self, key: str, text: str, encoding: str = "utf-8") -> str:
        """
        Write text to key.
        Returns the logical key (or URI) that was written.
        """

    @abstractmethod
    def exists(self, key: str) -> bool:
        """Return True if key exists."""

    @abstractmethod
    def open_read(self, key: str) -> BinaryIO:
        """
        Open a binary read stream for key.
        Caller is responsible for closing the stream.
        """

    @abstractmethod
    def list_keys(self, prefix: str = "") -> list[str]:
        """List keys under an optional prefix."""
