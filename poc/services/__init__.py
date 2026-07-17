"""Concrete storage services.

Only LocalStorageService is implemented for the POC.
S3StorageService is intentionally not implemented yet.
"""

from poc.services.storage_service import LocalStorageService, get_storage_service

__all__ = ["LocalStorageService", "get_storage_service"]
