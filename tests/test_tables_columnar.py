from trapezia_document_reader import extract_tables


def test_columnar_extracts_rows(columnar_pdf):
    tables = extract_tables(columnar_pdf, page_number=1, strategy="columnar")
    assert tables, "expected at least one table"
    flat = [cell for row in tables[0] for cell in row]
    assert "Widget" in flat and "12.0" in flat and "g/dL" in flat


def test_auto_picks_columnar_for_lineless(columnar_pdf):
    assert extract_tables(columnar_pdf, page_number=1, strategy="auto")


def test_auto_picks_ruled_for_grid(ruled_pdf):
    rows = extract_tables(ruled_pdf, page_number=1, strategy="auto")[0]
    assert rows[0] == ["Test", "Result", "Units", "Reference"]
