"""trapezia-document-reader: generic PDF read + OCR primitives."""

from trapezia_document_reader.columnar import (
    HEADER_SYNONYMS,
    assign_cells,
    clean_words,
    column_bounds,
    find_columns,
    group_rows,
    parse_date,
    parse_ref,
    row_text,
    split_value_unit,
)
from trapezia_document_reader.errors import (
    DocumentReadError,
    OcrError,
    OcrUnavailable,
)
from trapezia_document_reader.isolation import pdf_to_pages_isolated, run_isolated
from trapezia_document_reader.ocr import ocr_add_text_layer
from trapezia_document_reader.pages import PageDict, pdf_to_pages
from trapezia_document_reader.reader import read_pdf
from trapezia_document_reader.render import render_page_images
from trapezia_document_reader.scan import is_scanned
from trapezia_document_reader.tables import Table, extract_tables

__version__ = "0.3.1"

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
    "render_page_images",
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
