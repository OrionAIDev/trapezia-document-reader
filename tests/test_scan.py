from trapezia_document_reader import is_scanned


def test_born_digital_is_not_scanned(columnar_pdf):
    assert is_scanned(columnar_pdf) is False


def test_image_only_is_scanned(scanned_pdf):
    assert is_scanned(scanned_pdf) is True
