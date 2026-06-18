from trapezia_document_reader import pdf_to_pages


def test_pages_shape(columnar_pdf):
    pages = pdf_to_pages(columnar_pdf)
    assert len(pages) == 1
    p = pages[0]
    assert p["page"] == 1
    assert "Widget" in p["text"]
    assert set(p) == {"page", "text", "text_layout", "words", "lines"}
    assert all({"text", "x0", "x1", "top", "bottom"} <= set(w) for w in p["words"])


def test_ruled_pdf_has_lines(ruled_pdf):
    pages = pdf_to_pages(ruled_pdf)
    assert len(pages[0]["lines"]) > 0
