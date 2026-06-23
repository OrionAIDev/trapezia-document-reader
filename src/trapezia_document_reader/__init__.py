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
from trapezia_document_reader.ocr import ocr_add_text_layer
from trapezia_document_reader.reader import read_pdf
from trapezia_document_reader.columnar import (
    clean_words, group_rows, find_columns, column_bounds, assign_cells,
    row_text, split_value_unit, parse_ref, parse_date, HEADER_SYNONYMS,
)

__version__ = "0.2.1"

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
    "ocr_add_text_layer",
    "read_pdf",
    "clean_words",
    "group_rows",
    "find_columns",
    "column_bounds",
    "assign_cells",
    "row_text",
    "split_value_unit",
    "parse_ref",
    "parse_date",
    "HEADER_SYNONYMS",
]
