from trapezia_document_reader import extract_tables


def test_ruled_extracts_grid(ruled_pdf):
    tables = extract_tables(ruled_pdf, page_number=1, strategy="ruled")
    assert len(tables) == 1
    rows = tables[0]
    assert rows[0] == ["Test", "Result", "Units", "Reference"]
    assert ["Widget", "12.0", "g/dL", "10.0-15.0"] in rows
