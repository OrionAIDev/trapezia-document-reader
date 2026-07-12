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
    timeout: int | None = None,
) -> dict[str, Any]:
    """Return ``{pages, ocr_applied, source_path, working_path}``.

    ocr: "auto" (OCR iff scanned), "always", or "never".
    timeout: max seconds for the OCR step; ``None`` uses the OCR default.
    """
    if ocr not in {"auto", "always", "never"}:
        raise ValueError(f"ocr must be 'auto', 'always', or 'never'; got {ocr!r}")
    src = Path(path)
    do_ocr = ocr == "always" or (ocr == "auto" and is_scanned(src))
    if do_ocr:
        ocr_kwargs: dict[str, Any] = {"lang": lang}
        if timeout is not None:
            ocr_kwargs["timeout"] = timeout
        working = ocr_add_text_layer(src, **ocr_kwargs)
    else:
        working = src
    return {
        "pages": pdf_to_pages(working),
        "ocr_applied": bool(do_ocr),
        "source_path": str(src),
        "working_path": str(working),
    }
