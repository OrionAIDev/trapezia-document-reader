"""Exception types raised across the document-reader API."""


class DocumentReadError(Exception):
    """Raised when a PDF cannot be opened or parsed (corrupt, encrypted, timed out)."""


class OcrError(Exception):
    """Raised when an OCR pass fails."""


class OcrUnavailable(OcrError):
    """Raised when the OCR engine or its system binaries are not installed."""
