from trapezia_document_reader.columnar import parse_date


def test_winter_date_is_est_offset():
    assert parse_date("01/15/2026") == "2026-01-15T00:00:00-05:00"


def test_summer_date_is_edt_offset():
    assert parse_date("07/15/2026") == "2026-07-15T00:00:00-04:00"


def test_two_digit_year():
    assert parse_date("03/04/26").startswith("2026-03-04T00:00:00-0")


def test_unparseable_returns_none():
    assert parse_date("not-a-date") is None


def test_tz_override():
    assert parse_date("07/15/2026", tz="UTC") == "2026-07-15T00:00:00+00:00"
