from trapezia_document_reader.columnar import (
    assign_cells, clean_words, column_bounds, find_columns,
    group_rows, parse_ref, row_text, split_value_unit, HEADER_SYNONYMS,
)


def _w(text, x0, x1, top):
    return {"text": text, "x0": x0, "x1": x1, "top": top}


def test_group_rows_bands_by_y():
    words = [_w("A", 10, 20, 100), _w("B", 60, 70, 101), _w("C", 10, 20, 130)]
    rows = group_rows(words)
    assert [[w["text"] for w in r] for r in rows] == [["A", "B"], ["C"]]


def test_find_columns_detects_header():
    header = [_w("Test", 10, 40, 50), _w("Result", 100, 140, 50),
              _w("Units", 200, 240, 50), _w("Reference", 300, 360, 50)]
    cols = find_columns(header)
    assert cols is not None and {"test_name", "value", "units", "ref"} <= set(cols)


def test_assign_cells_by_band():
    header = [_w("Test", 10, 40, 50), _w("Result", 100, 140, 50),
              _w("Units", 200, 240, 50), _w("Reference", 300, 360, 50)]
    bands = column_bounds(find_columns(header))
    row = [_w("Glucose", 10, 60, 70), _w("92", 100, 120, 70),
           _w("mg/dL", 200, 240, 70), _w("70-99", 300, 350, 70)]
    cells = assign_cells(row, bands)
    assert cells["test_name"] == "Glucose" and cells["value"] == "92"
    assert cells["units"] == "mg/dL" and cells["ref"] == "70-99"


def test_split_value_unit():
    assert split_value_unit("13.2g/dL") == (13.2, None, "g/dL")
    assert split_value_unit("92") == (92.0, None, None)
    assert split_value_unit(">60") == (None, ">60", None)


def test_parse_ref():
    assert parse_ref("70-99") == {"low": 70.0, "high": 99.0, "text": "70-99"}
    assert parse_ref("<200")["high"] == 200.0
    assert parse_ref(">=60")["low"] == 60.0
