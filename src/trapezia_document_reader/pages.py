"""Turn a PDF into per-page text + geometry dicts (JSON-serializable)."""
from pathlib import Path
from typing import Any

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

PageDict = dict[str, Any]


def _word(w: dict) -> dict:
    return {
        "text": w.get("text", ""),
        "x0": float(w["x0"]),
        "x1": float(w["x1"]),
        "top": float(w["top"]),
        "bottom": float(w["bottom"]),
        "size": float(w.get("size", 0.0)),
    }


def _line(ln: dict) -> dict:
    return {
        "x0": float(ln["x0"]),
        "x1": float(ln["x1"]),
        "top": float(ln["top"]),
        "bottom": float(ln["bottom"]),
    }


def pdf_to_pages(path: str | Path) -> list[PageDict]:
    """Return one dict per page: text, layout-text, word boxes, line segments.

    The dict is a superset that keeps simple consumers (which read only
    ``page["text"]`` / ``page["page"]``) working unchanged, while exposing
    word x-positions and ruled lines for table extraction.
    """
    out: list[PageDict] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(extra_attrs=["size"]) or []
                out.append(
                    {
                        "page": i,
                        "text": page.extract_text() or "",
                        "text_layout": page.extract_text(layout=True) or "",
                        "words": [_word(w) for w in words],
                        "lines": [_line(ln) for ln in (page.lines or [])],
                    }
                )
    except DocumentReadError:
        raise
    except Exception as exc:
        raise DocumentReadError(f"cannot parse {path}: {exc}") from exc
    return out
