"""trapezia-document-reader: generic PDF read + OCR primitives."""

from trapezia_document_reader.errors import (
    DocumentReadError,
    OcrError,
    OcrUnavailable,
)
from trapezia_document_reader.scan import is_scanned

__version__ = "0.1.0"

__all__ = ["DocumentReadError", "OcrError", "OcrUnavailable", "__version__", "is_scanned"]
