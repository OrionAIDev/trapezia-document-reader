import pytest

from trapezia_document_reader import read_pdf


def test_born_digital_no_ocr(columnar_pdf):
    result = read_pdf(columnar_pdf, ocr="never")
    assert result["ocr_applied"] is False
    assert "Widget" in result["pages"][0]["text"]
    assert result["working_path"] == str(columnar_pdf)


def test_unknown_ocr_value_rejected(columnar_pdf):
    with pytest.raises(ValueError, match="ocr must be"):
        read_pdf(columnar_pdf, ocr="maybe")
