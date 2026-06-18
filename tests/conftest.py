from pathlib import Path

import pytest

FIX = Path(__file__).parent / "fixtures"


@pytest.fixture
def columnar_pdf() -> Path:
    return FIX / "born_digital_columnar.pdf"


@pytest.fixture
def ruled_pdf() -> Path:
    return FIX / "ruled_table.pdf"


@pytest.fixture
def scanned_pdf() -> Path:
    return FIX / "scanned_stub.pdf"
