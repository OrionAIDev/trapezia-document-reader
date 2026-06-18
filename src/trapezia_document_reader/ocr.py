"""Add a searchable text layer to a scanned PDF via ocrmypdf (out-of-process)."""
from pathlib import Path

from trapezia_document_reader.errors import OcrError, OcrUnavailable
from trapezia_document_reader.isolation import run_isolated


def _ocr_impl(src: str, dst: str, lang: str, force: bool) -> str:
    import ocrmypdf

    ocrmypdf.ocr(
        src,
        dst,
        language=lang,
        force_ocr=force,
        skip_text=not force,
        progress_bar=False,
    )
    return dst


def ocr_add_text_layer(
    path: str | Path,
    *,
    out_path: str | Path | None = None,
    lang: str = "eng",
    force: bool = False,
    timeout: int = 120,
) -> Path:
    """Return a NEW PDF with an invisible OCR text layer; input untouched.

    Idempotent: a PDF that already has text is passed through (``skip_text``)
    unless ``force``. Runs ocrmypdf in a worker process under ``timeout`` so a
    pathological scan can't hang the caller.
    """
    src = Path(path)
    dst = Path(out_path) if out_path else src.with_suffix(".ocr.pdf")
    try:
        import ocrmypdf  # noqa: F401
    except ImportError as exc:
        raise OcrUnavailable("ocrmypdf is not installed (pip install '.[ocr]')") from exc
    try:
        run_isolated(_ocr_impl, str(src), str(dst), lang, force, timeout=timeout)
    except Exception as exc:
        msg = str(exc).lower()
        if "tesseract" in msg or "ghostscript" in msg or "not found" in msg:
            raise OcrUnavailable(f"OCR system binary missing: {exc}") from exc
        raise OcrError(f"OCR failed for {src}: {exc}") from exc
    return dst
