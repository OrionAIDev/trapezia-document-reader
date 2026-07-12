"""Add a searchable text layer to a scanned PDF via ocrmypdf (out-of-process)."""
import os
import tempfile
from pathlib import Path

from trapezia_document_reader.errors import OcrError, OcrUnavailable
from trapezia_document_reader.isolation import run_isolated

# Default OCR ceiling. Generous because the Ghostscript-10 fallback re-OCRs every
# page (force_ocr), which is far slower than skip_text; a large scan legitimately
# takes minutes. Callers may override via ``timeout=``.
DEFAULT_OCR_TIMEOUT = 600


def _ocr_impl(src: str, dst: str, lang: str, force: bool, opts: dict) -> str:
    import ocrmypdf

    def _run(force_ocr: bool) -> None:
        ocrmypdf.ocr(
            src,
            dst,
            language=lang,
            force_ocr=force_ocr,
            skip_text=not force_ocr,
            progress_bar=False,
            **opts,
        )

    try:
        _run(force_ocr=force)
    except Exception as exc:  # noqa: BLE001 — narrowed by the gs-guard signature below
        # Debian bookworm's Ghostscript (10.0.0) is on ocrmypdf's deny-list for the
        # --skip-text/--redo-ocr paths (that gs range can corrupt PDFs with existing
        # text). When that guard blocks the lossless skip_text attempt, fall back to
        # --force-ocr (re-OCR every page) so extraction still succeeds. Only the
        # version guard is retried; a genuinely missing binary or unrelated error
        # (and an explicit force=True request) propagates unchanged.
        msg = str(exc).lower()
        gs_guard = "ghostscript" in msg and (
            "--force-ocr" in msg or "regressions" in msg or "skip-text" in msg
        )
        if force or not gs_guard:
            raise
        _run(force_ocr=True)
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
    timeout: int = DEFAULT_OCR_TIMEOUT,
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
    if out_path is not None:
        dst = Path(out_path)
    else:
        # Write the intermediate OCR'd PDF to a temp file, NOT next to the source:
        # the source may live in a read-only mount (e.g. a wiki vault raw/ dir), and
        # a sibling ``.ocr.pdf`` there fails with OutputFileAccessError.
        fd, tmp = tempfile.mkstemp(prefix=f"{src.stem}.", suffix=".ocr.pdf")
        os.close(fd)
        dst = Path(tmp)
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
