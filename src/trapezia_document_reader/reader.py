"""High-level convenience: OCR-if-needed, then return pages."""
from pathlib import Path
from typing import Any

from trapezia_document_reader.ocr import ocr_add_text_layer
from trapezia_document_reader.pages import pdf_to_pages
from trapezia_document_reader.scan import is_scanned


def read_pdf(
    path: str | Path,
    *,
    ocr: str = "auto",
    lang: str = "eng",
) -> dict[str, Any]:
    """Return ``{pages, ocr_applied, source_path, working_path}``.

    ocr: "auto" (OCR iff scanned), "always", or "never".
    """
    src = Path(path)
    do_ocr = ocr == "always" or (ocr == "auto" and is_scanned(src))
    working = ocr_add_text_layer(src, lang=lang) if do_ocr else src
    return {
        "pages": pdf_to_pages(working),
        "ocr_applied": bool(do_ocr),
        "source_path": str(src),
        "working_path": str(working),
    }
