import shutil

import pytest

from trapezia_document_reader import is_scanned, ocr_add_text_layer, pdf_to_pages

pytest.importorskip("ocrmypdf")
if shutil.which("tesseract") is None:
    pytest.skip("tesseract binary not installed", allow_module_level=True)


def test_ocr_makes_scanned_readable(scanned_pdf, tmp_path):
    # Default path now applies deskew=True; the round-trip must still work.
    assert is_scanned(scanned_pdf) is True
    out = ocr_add_text_layer(scanned_pdf, out_path=tmp_path / "ocr.pdf")
    assert out.exists()
    assert is_scanned(out) is False
    text = " ".join(p["text"] for p in pdf_to_pages(out))
    assert "Widget" in text


def test_ocr_tuning_params_pass_through(scanned_pdf, tmp_path):
    # The ocrmypdf quality knobs must be accepted and produce a valid OCR'd PDF
    # (proves the kwargs reach ocrmypdf.ocr without TypeError across the worker
    # process). tesseract_pagesegmode 6 = assume a single uniform block.
    out = ocr_add_text_layer(
        scanned_pdf,
        out_path=tmp_path / "tuned.pdf",
        deskew=True,
        tesseract_psm=6,
    )
    assert out.exists()
    text = " ".join(p["text"] for p in pdf_to_pages(out))
    assert "Widget" in text
