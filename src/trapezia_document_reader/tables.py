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


def _column_bands(words, tol: float = 12.0) -> list[float]:
    """Cluster word left-edges (x0) into columns; return vertical-line x-coords.

    Lines are placed midway between one column's rightmost x1 and the next
    column's leftmost x0, plus outer bounds.
    """
    if not words:
        return []
    starts = sorted(w["x0"] for w in words)
    clusters: list[list[float]] = [[starts[0]]]
    for x in starts[1:]:
        if x - clusters[-1][-1] <= tol:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    col_left = [min(c) for c in clusters]
    # rightmost x1 of any word belonging (by nearest start) to each column
    col_right = list(col_left)
    for w in words:
        ci = min(range(len(col_left)), key=lambda i: abs(w["x0"] - col_left[i]))
        col_right[ci] = max(col_right[ci], w["x1"])
    lines = [col_left[0] - 2.0]
    for i in range(len(col_left) - 1):
        lines.append((col_right[i] + col_left[i + 1]) / 2.0)
    lines.append(col_right[-1] + 2.0)
    return lines


def _columnar(page, column_hints: list[float] | None) -> list["Table"]:
    words = [
        {"x0": float(w["x0"]), "x1": float(w["x1"])}
        for w in (page.extract_words() or [])
    ]
    verticals = column_hints if column_hints else _column_bands(words)
    if len(verticals) < 2:
        return []
    settings = {
        "vertical_strategy": "explicit",
        "explicit_vertical_lines": verticals,
        "horizontal_strategy": "text",
    }
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
            if strategy == "columnar":
                return _columnar(page, column_hints)
            if strategy == "auto":
                return _ruled(page) if page.lines else _columnar(page, column_hints)
            raise ValueError(f"unknown strategy: {strategy}")
    except (DocumentReadError, ValueError):
        raise
    except Exception as exc:
        raise DocumentReadError(f"cannot extract tables from {path}: {exc}") from exc
