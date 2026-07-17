from __future__ import annotations


class ProcessingError(Exception):
    """Base class for handled pipeline failures (never crash the engine)."""

    code: str = "PROCESSING_ERROR"
    status: str = "FAILED"

    def __init__(self, message: str, *, warnings: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.warnings = warnings or []


class EmptyPDFError(ProcessingError):
    code = "EMPTY_PDF"


class CorruptedPDFError(ProcessingError):
    code = "CORRUPTED_PDF"


class PasswordProtectedPDFError(ProcessingError):
    code = "PASSWORD_PROTECTED_PDF"


class UnsupportedDocumentError(ProcessingError):
    code = "UNSUPPORTED_DOCUMENT"


class OCRFailureError(ProcessingError):
    code = "OCR_FAILURE"


class MissingHoldingTableError(ProcessingError):
    code = "MISSING_HOLDING_TABLE"


class FileTooLargeError(ProcessingError):
    code = "FILE_TOO_LARGE"


class MaxPagesExceededError(ProcessingError):
    code = "MAX_PAGES_EXCEEDED"
