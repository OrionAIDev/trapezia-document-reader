"""Rasterize PDF pages to PNG image bytes via pypdfium2.

Used by the vision-LLM lab extractor (trapezia-salus #71): when a scanned PDF's
OCR'd text is too lossy to extract reliably, the page *image* is sent to a
multimodal model instead. pypdfium2 + Pillow are pure-wheel deps (no system
binaries, unlike the OCR extra), so this stays in the core install.
"""
from __future__ import annotations

import io
from collections.abc import Sequence
from pathlib import Path

from trapezia_document_reader.errors import DocumentReadError


def render_page_images(
    path: str | Path,
    *,
    dpi: int = 200,
    pages: Sequence[int] | None = None,
) -> list[bytes]:
    """Rasterize PDF pages to PNG bytes, one blob per page.

    Args:
        path: Path to the PDF file.
        dpi: Rasterization resolution. 200 is a good default for lab-report text;
            higher recovers finer detail at the cost of larger payloads.
        pages: Zero-based page indices to render, in order. ``None`` renders every
            page.

    Returns:
        A list of PNG-encoded byte blobs, one per rendered page, in ``pages`` order
        (or document order when ``pages`` is ``None``).

    Raises:
        DocumentReadError: If the PDF cannot be found, opened, or rendered.
    """
    import pypdfium2 as pdfium

    src = Path(path)
    if not src.exists():
        raise DocumentReadError(f"PDF not found: {src}")
    try:
        pdf = pdfium.PdfDocument(str(src))
    except Exception as exc:
        raise DocumentReadError(f"cannot open PDF {src}: {exc}") from exc
    try:
        indices = range(len(pdf)) if pages is None else pages
        scale = dpi / 72.0
        out: list[bytes] = []
        for i in indices:
            bitmap = pdf[i].render(scale=scale)
            buf = io.BytesIO()
            bitmap.to_pil().convert("RGB").save(buf, format="PNG")
            out.append(buf.getvalue())
        return out
    except Exception as exc:
        raise DocumentReadError(f"cannot render PDF {src}: {exc}") from exc
    finally:
        pdf.close()
