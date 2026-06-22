"""Generic columnar table-geometry core for whitespace-aligned PDFs.

This module holds the clinical-agnostic primitives shared by Trapezia
consumers for reading whitespace-columnar tables out of born-digital PDFs:
word normalisation, y-band row grouping, column-header detection, x-band cell
assignment, and value/reference-interval parsing, plus the default
column-synonym map.

It carries NO vocabulary specific to any domain (no clinical flags, panels, or
categories) — those live with the consuming vendor. Brand-specific extra
header synonyms can be merged in by the caller before invoking
:func:`find_columns`.
"""
from __future__ import annotations

import re

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------
Y_TOL = 3.0  # words within this many points of `top` share a row

# Canonical column synonyms (lowercased) -> logical field. Shared by every
# whitespace-columnar vendor; brand-specific extra synonyms can be merged in by
# the vendor before calling find_columns.
HEADER_SYNONYMS: dict[str, str] = {
    "tests": "test_name",
    "test": "test_name",
    "analyte": "test_name",
    "analytes": "test_name",
    "component": "test_name",
    "components": "test_name",
    "name": "test_name",
    "result": "value",
    "results": "value",
    "value": "value",
    "flag": "flag",
    "abnormal": "flag",
    "units": "units",
    "unit": "units",
    "reference": "ref",  # "Reference Interval" / "Reference Range" — first word
    "ref": "ref",
    "range": "ref",
    "interval": "ref",
    "lab": "lab",
}

# ---------------------------------------------------------------------------
# Regex
# ---------------------------------------------------------------------------
_VALUE_GLUED = re.compile(
    r"^(?P<num>[<>]?=?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?)"
    r"\s*(?P<unit>[A-Za-z%/][A-Za-z%/0-9.*\-]*)?$"
)
PURE_NUMBER = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$")
_REF_BOUNDED = re.compile(r"^(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)$")
_REF_UPPER = re.compile(r"^<\s*=?\s*(-?\d+(?:\.\d+)?)$")  # <X / <=X -> high
_REF_LOWER = re.compile(r"^>\s*=?\s*(-?\d+(?:\.\d+)?)$")  # >X / >=X -> low

QUAL_OK = re.compile(
    r"^(negative|positive|reactive|non-?reactive|detected|not detected|none"
    r"|trace|normal|abnormal|present|absent|see note|pending|clear|yellow)\b",
    re.IGNORECASE,
)

_BARE_NUMBER = re.compile(r"^[<>]?=?\s*-?\d{1,3}(?:,\d{3})*(?:\.\d+)?$")


def _word_x0(w: dict) -> float:
    return float(w.get("x0", 0.0))


def clean_words(words: list[dict]) -> list[dict]:
    """Normalise raw pdfplumber word dicts into the minimal shape we consume.

    ``extract_words()`` already groups consecutive characters into whole,
    whitespace-delimited words, so NO re-merging is done here. We only coerce
    ``x0``/``x1``/``top`` to floats, drop empty/positionless words, and keep the
    fields the row/column logic needs.
    """
    clean: list[dict] = []
    for w in words:
        try:
            text = str(w.get("text", ""))
            x0 = float(w["x0"])
            x1 = float(w["x1"])
            top = float(w["top"])
        except (KeyError, TypeError, ValueError):
            continue
        if not text:
            continue
        clean.append({"text": text, "x0": x0, "x1": x1, "top": top})
    return clean


def group_rows(words: list[dict]) -> list[list[dict]]:
    """Group words into rows by y-band; each row sorted left-to-right."""
    rows: list[list[dict]] = []
    current: list[dict] = []
    current_top: float | None = None
    for w in sorted(words, key=lambda w: (w["top"], w["x0"])):
        if current_top is None or abs(w["top"] - current_top) <= Y_TOL:
            current.append(w)
            current_top = w["top"] if current_top is None else current_top
        else:
            rows.append(sorted(current, key=_word_x0))
            current = [w]
            current_top = w["top"]
    if current:
        rows.append(sorted(current, key=_word_x0))
    return rows


def find_columns(
    row: list[dict], synonyms: dict[str, str] | None = None
) -> dict[str, tuple[float, float]] | None:
    """If ``row`` is a column-header row, return {field: (x0, x1)} anchors.

    ``synonyms`` defaults to the canonical :data:`HEADER_SYNONYMS`; a vendor may
    pass an extended map.
    """
    syn = synonyms if synonyms is not None else HEADER_SYNONYMS
    fields: dict[str, tuple[float, float]] = {}
    matched = 0
    for w in row:
        key = w["text"].strip().lower().rstrip(":")
        field = syn.get(key)
        if field is None:
            continue
        matched += 1
        # First word of a multi-word header (e.g. "Reference") anchors the band;
        # extend the band's right edge with later header words of the same field.
        if field in fields:
            fields[field] = (fields[field][0], w["x1"])
        else:
            fields[field] = (w["x0"], w["x1"])
    # Require at least the test-name + value columns to call it a header.
    if "test_name" in fields and "value" in fields and matched >= 3:
        return fields
    return None


def column_bounds(
    cols: dict[str, tuple[float, float]]
) -> list[tuple[str, float, float]]:
    """Turn header anchors into ordered (field, left, right) assignment bands.

    Each column owns the span from a point midway to the previous header to a
    point midway to the next header (first column extends to -inf, last to
    +inf), so data words that sit slightly off their header still land in the
    right column.
    """
    ordered = sorted(cols.items(), key=lambda kv: kv[1][0])
    bands: list[tuple[str, float, float]] = []
    for i, (field, (left, _right)) in enumerate(ordered):
        if i == 0:
            lo = float("-inf")
        else:
            prev_left = ordered[i - 1][1][0]
            lo = (prev_left + left) / 2.0
        if i == len(ordered) - 1:
            hi = float("inf")
        else:
            next_left = ordered[i + 1][1][0]
            hi = (left + next_left) / 2.0
        bands.append((field, lo, hi))
    return bands


def assign_cells(
    row: list[dict], bands: list[tuple[str, float, float]]
) -> dict[str, str]:
    """Assign each word in ``row`` to a column band by x-center; join per field."""
    cells: dict[str, list[str]] = {}
    for w in row:
        cx = (w["x0"] + w["x1"]) / 2.0
        for field, lo, hi in bands:
            if lo <= cx < hi:
                cells.setdefault(field, []).append(w["text"])
                break
    return {k: " ".join(v).strip() for k, v in cells.items()}


def row_text(row: list[dict]) -> str:
    """Join a row's words left-to-right into a single space-separated string."""
    return " ".join(w["text"] for w in row).strip()


def split_value_unit(raw: str) -> tuple[float | None, str | None, str | None]:
    """Return (value, value_string, glued_unit) from a result cell.

    Numeric (possibly with a glued unit like ``13.2g/dL``) -> value + unit.
    A result carrying a comparator (``>60``/``<=0.01``) keeps the full token in
    ``value_string`` (``value`` None) so the operator is not silently dropped.
    Qualitative (Negative/Positive/…) -> ``value_string``.
    """
    s = raw.strip()
    if not s:
        return None, None, None
    m = _VALUE_GLUED.match(s)
    if m:
        num = m.group("num").replace(" ", "").replace(",", "")
        if num.lstrip().startswith(("<", ">")):
            return None, s, None
        try:
            value = float(num)
        except ValueError:
            return None, s, None
        unit = m.group("unit")
        unit = unit.strip() if unit else None
        return value, None, unit or None
    return None, s, None


def parse_ref(raw: str | None) -> dict | None:
    """Parse a reference-interval cell to {low, high, text} or None.

    ``a-b`` -> bounded; ``<x``/``<=x`` -> high only; ``>x``/``>=x`` -> low only;
    anything else with content -> free text (low/high None).
    """
    if not raw:
        return None
    s = raw.strip()
    if not s:
        return None
    m = _REF_BOUNDED.match(s)
    if m:
        low, high = float(m.group(1)), float(m.group(2))
        return {"low": low, "high": high, "text": s}
    m = _REF_UPPER.match(s)
    if m:
        return {"low": None, "high": float(m.group(1)), "text": s}
    m = _REF_LOWER.match(s)
    if m:
        return {"low": float(m.group(1)), "high": None, "text": s}
    return {"low": None, "high": None, "text": s}


# ---------------------------------------------------------------------------
# Back-compat underscore aliases for salus vendor modules that import the
# private names. Only the symbols present in this module are aliased here.
# ---------------------------------------------------------------------------
_clean_words = clean_words
_group_rows = group_rows
_find_columns = find_columns
_column_bounds = column_bounds
_assign_cells = assign_cells
_row_text = row_text
_split_value_unit = split_value_unit
_parse_ref = parse_ref
