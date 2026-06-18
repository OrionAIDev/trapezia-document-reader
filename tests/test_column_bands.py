from trapezia_document_reader.tables import _column_bands


def test_band_separator_uses_true_cluster_membership():
    # Column A chains 10->22->34->46 (each gap == tol=12); its widest word ends
    # at x1=50. Column B starts at x0=60. A naive nearest-left-edge assignment
    # would attribute the x0=46 word to B, shrink column A's right edge, and put
    # the interior separator at ~49 -- cutting through column A's widest word.
    words = [
        {"x0": 10, "x1": 14}, {"x0": 22, "x1": 26},
        {"x0": 34, "x1": 38}, {"x0": 46, "x1": 50},
        {"x0": 60, "x1": 64},
    ]
    lines = _column_bands(words, tol=12.0)
    assert len(lines) == 3  # two columns -> outer, interior, outer
    interior = lines[1]
    # separator must sit in the gap to the RIGHT of column A's widest word (x1=50)
    assert 50 <= interior <= 60


def test_empty_words_returns_empty():
    assert _column_bands([]) == []
