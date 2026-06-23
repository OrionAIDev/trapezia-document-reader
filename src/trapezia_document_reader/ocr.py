"""Add a searchable text layer to a scanned PDF via ocrmypdf (out-of-process)."""
from pathlib import Path

from trapezia_document_reader.errors import OcrError, OcrUnavailable
from trapezia_document_reader.isolation import run_isolated


def _ocr_impl(src: str, dst: str, lang: str, force: bool, opts: dict) -> str:
    import ocrmypdf

    ocrmypdf.ocr(
        src,
        dst,
        language=lang,
        force_ocr=force,
        skip_text=not force,
        progress_bar=False,
        **opts,
    )
    return dst


def ocr_add_text_layer(
    path: str | Path,
    *,
    out_path: str | Path | None = None,
    lang: str = "eng",
    force: bool = False,
    deskew: bool = True,
    rotate: bool = False,
    clean: bool = False,
    oversample: int | None = None,
    optimize: int | None = None,
    tesseract_psm: int | None = None,
    timeout: int = 120,
) -> Path:
    """Return a NEW PDF with an invisible OCR text layer; input untouched.

    Idempotent: a PDF that already has text is passed through (``skip_text``)
    unless ``force``. Runs ocrmypdf in a worker process under ``timeout`` so a
    pathological scan can't hang the caller.

    Quality knobs (passed through to ocrmypdf) for tuning OCR on imperfect
    scans — accuracy on low-quality source scans is ultimately bounded by the
    scan itself, so callers should still treat OCR'd output as low-confidence:

    * ``deskew`` (default ``True``) — straighten skewed pages before OCR. Safe
      and generally helpful; uses Leptonica, no extra system binary.
    * ``rotate`` — auto-rotate pages by tesseract OSD (needs ``osd`` tessdata).
    * ``clean`` — denoise before OCR; requires the ``unpaper`` system binary,
      so it is off by default (a missing ``unpaper`` raises ``OcrUnavailable``).
    * ``oversample`` — rasterize at this DPI (e.g. 300/400) for low-DPI scans.
    * ``optimize`` — ocrmypdf output optimization level (0–3).
    * ``tesseract_psm`` — tesseract page-segmentation mode (e.g. 6 for a uniform
      block — sometimes reads tabular lab columns better than the default).
    """
    src = Path(path)
    dst = Path(out_path) if out_path else src.with_suffix(".ocr.pdf")
    try:
        import ocrmypdf  # noqa: F401
    except ImportError as exc:
        raise OcrUnavailable("ocrmypdf is not installed (pip install '.[ocr]')") from exc
    opts: dict = {"deskew": deskew, "rotate_pages": rotate, "clean": clean}
    if oversample is not None:
        opts["oversample"] = oversample
    if optimize is not None:
        opts["optimize"] = optimize
    if tesseract_psm is not None:
        opts["tesseract_pagesegmode"] = tesseract_psm
    try:
        run_isolated(_ocr_impl, str(src), str(dst), lang, force, opts, timeout=timeout)
    except Exception as exc:
        msg = str(exc).lower()
        if "tesseract" in msg or "ghostscript" in msg or "unpaper" in msg or "not found" in msg:
            raise OcrUnavailable(f"OCR system binary missing: {exc}") from exc
        raise OcrError(f"OCR failed for {src}: {exc}") from exc
    return dst
