from trapezia_document_reader import (
    DocumentReadError,
    OcrError,
    OcrUnavailable,
    __version__,
)


def test_error_hierarchy():
    assert issubclass(OcrUnavailable, OcrError)
    assert issubclass(DocumentReadError, Exception)


def test_version_exposed():
    assert __version__ == "0.3.0"
