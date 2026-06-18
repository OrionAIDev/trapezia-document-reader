"""trapezia-document-reader: generic PDF read + OCR primitives."""

from trapezia_document_reader.errors import (
    DocumentReadError,
    OcrError,
    OcrUnavailable,
)
from trapezia_document_reader.pages import pdf_to_pages, PageDict
from trapezia_document_reader.isolation import pdf_to_pages_isolated, run_isolated
from trapezia_document_reader.scan import is_scanned
from trapezia_document_reader.tables import extract_tables, Table

__version__ = "0.1.0"

__all__ = [
    "DocumentReadError",
    "OcrError",
    "OcrUnavailable",
    "__version__",
    "is_scanned",
    "pdf_to_pages",
    "PageDict",
    "extract_tables",
    "Table",
    "run_isolated",
    "pdf_to_pages_isolated",
]
