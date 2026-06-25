"""Tests for render_page_images — rasterize PDF pages to PNG bytes (#71)."""
import pytest

from trapezia_document_reader import pdf_to_pages, render_page_images
from trapezia_document_reader.errors import DocumentReadError

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


def test_render_returns_one_png_per_page(columnar_pdf):
    expected_pages = len(pdf_to_pages(columnar_pdf))
    imgs = render_page_images(columnar_pdf)
    assert isinstance(imgs, list)
    assert len(imgs) == expected_pages
    assert expected_pages >= 1
    for blob in imgs:
        assert isinstance(blob, (bytes, bytearray))
        assert blob[:8] == _PNG_MAGIC


def test_render_pages_selector_limits_output(columnar_pdf):
    imgs = render_page_images(columnar_pdf, pages=[0])
    assert len(imgs) == 1
    assert imgs[0][:8] == _PNG_MAGIC


def test_render_higher_dpi_yields_larger_image(columnar_pdf):
    low = render_page_images(columnar_pdf, dpi=72, pages=[0])[0]
    high = render_page_images(columnar_pdf, dpi=300, pages=[0])[0]
    assert len(high) > len(low)


def test_render_missing_file_raises_document_read_error(tmp_path):
    with pytest.raises(DocumentReadError):
        render_page_images(tmp_path / "does-not-exist.pdf")
