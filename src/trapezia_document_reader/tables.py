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

    Words are sorted by x0 and grouped greedily: a word joins the current
    column when its x0 is within ``tol`` of the previous word's x0, else it
    starts a new column. Each separator is placed midway between one column's
    rightmost edge (the max x1 of its actual members) and the next column's
    leftmost edge, with a small outer pad on each side.

    Assumes the inter-column gap exceeds the intra-column x0 spread (true for
    whitespace-aligned reports); denser or overlapping columns may merge.
    """
    if not words:
        return []
    ordered = sorted(words, key=lambda w: w["x0"])
    clusters: list[list[dict]] = [[ordered[0]]]
    for w in ordered[1:]:
        if w["x0"] - clusters[-1][-1]["x0"] <= tol:
            clusters[-1].append(w)
        else:
            clusters.append([w])
    col_left = [min(w["x0"] for w in c) for c in clusters]
    col_right = [max(w["x1"] for w in c) for c in clusters]
    lines = [col_left[0] - 2.0]
    for i in range(len(clusters) - 1):
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
