"""Processing pipeline — storage-agnostic.

Depends on StorageService interface only (injected), not local disk or S3.
"""

from poc.pipeline.runner import run_pipeline

__all__ = ["run_pipeline"]
