"""Detect whether a PDF is a born-digital text PDF or an image-only scan."""
from pathlib import Path

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

SCANNED_TEXT_THRESHOLD = 50
SCANNED_SAMPLE_PAGES = 5


def is_scanned(path: str | Path) -> bool:
    """Return True if the sampled pages carry almost no text but do carry images.

    Samples the first ``SCANNED_SAMPLE_PAGES`` pages: scanned iff the total
    non-whitespace character count is below ``SCANNED_TEXT_THRESHOLD`` while at
    least one sampled page has image objects.
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = pdf.pages[:SCANNED_SAMPLE_PAGES]
            if not pages:
                return False
            text_chars = 0
            has_images = False
            for page in pages:
                stripped = "".join((page.extract_text() or "").split())
                text_chars += len(stripped)
                if page.images:
                    has_images = True
    except Exception as exc:
        raise DocumentReadError(f"cannot open {path}: {exc}") from exc
    return text_chars < SCANNED_TEXT_THRESHOLD and has_images
