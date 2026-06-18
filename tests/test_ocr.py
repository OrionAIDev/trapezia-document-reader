import shutil

import pytest

from trapezia_document_reader import is_scanned, ocr_add_text_layer, pdf_to_pages

pytest.importorskip("ocrmypdf")
if shutil.which("tesseract") is None:
    pytest.skip("tesseract binary not installed", allow_module_level=True)


def test_ocr_makes_scanned_readable(scanned_pdf, tmp_path):
    assert is_scanned(scanned_pdf) is True
    out = ocr_add_text_layer(scanned_pdf, out_path=tmp_path / "ocr.pdf")
    assert out.exists()
    assert is_scanned(out) is False
    text = " ".join(p["text"] for p in pdf_to_pages(out))
    assert "Widget" in text
