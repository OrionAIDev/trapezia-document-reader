"""Detect whether a PDF is a born-digital text PDF or an image-only scan."""
from pathlib import Path

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

SCANNED_TEXT_THRESHOLD = 50


def is_scanned(path: str | Path) -> bool:
    """Return True if page 0 has no real text layer but carries images.

    Cheap gate (opens page 0 only). Used to decide whether OCR must run
    before the page can be parsed.
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            if not pdf.pages:
                return False
            page = pdf.pages[0]
            text = page.extract_text() or ""
            has_images = bool(page.images)
    except Exception as exc:  # pdfplumber/pdfminer raise a variety of types
        raise DocumentReadError(f"cannot open {path}: {exc}") from exc
    return len(text.strip()) < SCANNED_TEXT_THRESHOLD and has_images
