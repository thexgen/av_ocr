"""Processing pipeline — storage-agnostic.

Depends on StorageService interface only (injected), not local disk or S3.
"""

from backend.pipeline.runner import run_pipeline

__all__ = ["run_pipeline"]
