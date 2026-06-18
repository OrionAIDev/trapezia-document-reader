import time

import pytest

from trapezia_document_reader import DocumentReadError
from trapezia_document_reader.isolation import pdf_to_pages_isolated, run_isolated


def _add(a, b):
    return a + b


def _sleep(seconds):
    time.sleep(seconds)
    return "done"


def test_run_isolated_returns_value():
    assert run_isolated(_add, 2, 3, timeout=10) == 5


def test_run_isolated_times_out():
    with pytest.raises(DocumentReadError):
        run_isolated(_sleep, 5, timeout=1)


def test_pdf_to_pages_isolated(columnar_pdf):
    pages = pdf_to_pages_isolated(columnar_pdf, timeout=30)
    assert pages[0]["page"] == 1 and "Widget" in pages[0]["text"]
