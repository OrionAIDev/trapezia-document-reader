import importlib.metadata

import trapezia_document_reader as tdr


def test_public_surface():
    expected = {
        "is_scanned", "pdf_to_pages", "PageDict", "extract_tables", "Table",
        "ocr_add_text_layer", "read_pdf", "run_isolated", "pdf_to_pages_isolated",
        "DocumentReadError", "OcrError", "OcrUnavailable", "__version__",
    }
    assert expected <= set(tdr.__all__)
    for name in expected:
        assert hasattr(tdr, name)


def test_version_matches_metadata():
    assert tdr.__version__ == importlib.metadata.version("trapezia-document-reader")
