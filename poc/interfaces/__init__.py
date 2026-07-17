"""Storage abstractions.

Business/pipeline code depends only on these interfaces.
Local disk is the current implementation; S3 can replace it later
without changing pipeline logic.
"""

from poc.interfaces.storage import StorageService

__all__ = ["StorageService"]
