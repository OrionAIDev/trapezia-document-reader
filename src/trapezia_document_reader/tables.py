"""Generic table extraction: ruled grids and whitespace-columnar layouts.

Returns raw cell strings only — no header detection or semantic mapping.
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


def extract_tables(
    path: str | Path,
    page_number: int,
    *,
    strategy: str = "auto",
    column_hints: list[float] | None = None,
) -> list[Table]:
    """Extract tables from one page (1-based).

    strategy: "ruled" (use page lines), "columnar" (whitespace bands),
    or "auto" (ruled if the page has lines, else columnar).
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            page = pdf.pages[page_number - 1]
            if strategy == "ruled":
                return _ruled(page)
            raise NotImplementedError(strategy)  # columnar/auto land in Task 6
    except (DocumentReadError, NotImplementedError):
        raise
    except Exception as exc:
        raise DocumentReadError(f"cannot extract tables from {path}: {exc}") from exc
