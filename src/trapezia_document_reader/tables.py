"""Generic ruled-table extraction: line-delimited grids only.

Returns raw cell strings — no header detection or semantic mapping. Whitespace-
columnar layouts are handled by :mod:`trapezia_document_reader.columnar`.
"""
from pathlib import Path

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

Table = list[list[str]]


def _clean(rows) -> Table:
    out: Table = []
    for row in rows:
        out.append([(c or "").strip() for c in row])
    return out


def _ruled(page) -> list[Table]:
    settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    return [_clean(t) for t in (page.extract_tables(settings) or [])]


def extract_tables(path: str | Path, page_number: int, *, strategy: str = "ruled") -> list[Table]:
    """Extract ruled (line-delimited) tables from one page (1-based).

    Only the ``ruled`` strategy remains: whitespace-columnar extraction now lives
    in :mod:`trapezia_document_reader.columnar` (``group_rows``/``find_columns``/
    ``column_bounds``/``assign_cells``), which the lab extractors compose directly.
    """
    if strategy != "ruled":
        raise ValueError(f"only 'ruled' is supported; for columnar use the columnar primitives (got {strategy!r})")
    try:
        with pdfplumber.open(str(path)) as pdf:
            page = pdf.pages[page_number - 1]
            return _ruled(page)
    except (DocumentReadError, ValueError):
        raise
    except Exception as exc:
        raise DocumentReadError(f"cannot extract tables from {path}: {exc}") from exc
