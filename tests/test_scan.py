from trapezia_document_reader import is_scanned


def test_born_digital_is_not_scanned(columnar_pdf):
    assert is_scanned(columnar_pdf) is False


def test_image_only_is_scanned(scanned_pdf):
    assert is_scanned(scanned_pdf) is True


def test_multipage_sampling_uses_more_than_page_zero(columnar_pdf):
    # columnar fixture is single-page born-digital; still must be False.
    assert is_scanned(columnar_pdf) is False
