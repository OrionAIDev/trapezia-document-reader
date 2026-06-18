# trapezia-document-reader Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `trapezia-document-reader`, a clinical-agnostic pip library that turns a PDF (born-digital or scanned) into text + geometry + generic table rows, with OCR via ocrmypdf and out-of-process isolation.

**Architecture:** Pure-read functions over pdfplumber return JSON-serializable page dicts (no pdfplumber objects leak across the API). OCR is a pre-pass (`ocrmypdf` adds a text layer so downstream parsing is unchanged). Heavy calls run in a `multiprocessing` worker under a timeout so a malformed/huge PDF can't hang or OOM the caller. No LLM, no clinical logic.

**Tech Stack:** Python 3.11+, pdfplumber (base), ocrmypdf (`[ocr]` extra → system tesseract+ghostscript), pytest + reportlab + Pillow (dev fixtures), Sphinx (docs).

**Spec:** `docs/superpowers/specs/2026-06-18-trapezia-document-reader-design.md`

---

## File Structure

```
pyproject.toml
src/trapezia_document_reader/
  __init__.py        # public exports + __version__
  errors.py          # DocumentReadError, OcrError, OcrUnavailable
  scan.py            # is_scanned
  pages.py           # pdf_to_pages, PageDict
  tables.py          # extract_tables (ruled + columnar + auto)
  ocr.py             # ocr_add_text_layer
  isolation.py       # run_isolated + pdf_to_pages_isolated
  reader.py          # read_pdf convenience
tests/
  conftest.py        # fixture paths
  fixtures/build_fixtures.py  # reportlab/Pillow synthetic PDF builder
  fixtures/*.pdf     # generated, committed
  test_*.py
docs/                # sphinx (Task 10)
```

---

## Task 1: Project scaffold + errors module

**Files:**
- Create: `pyproject.toml`
- Create: `src/trapezia_document_reader/__init__.py`
- Create: `src/trapezia_document_reader/errors.py`
- Test: `tests/test_errors.py`

- [ ] **Step 1: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "trapezia-document-reader"
version = "0.1.0"
description = "Clinical-agnostic PDF read + OCR primitives for the Trapezia platform"
requires-python = ">=3.11"
dependencies = ["pdfplumber>=0.11,<1.0"]

[project.optional-dependencies]
ocr = ["ocrmypdf>=16,<17"]
dev = ["pytest>=8", "reportlab>=4", "pillow>=10"]

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

- [ ] **Step 2: Write `errors.py`**

```python
"""Exception types raised across the document-reader API."""


class DocumentReadError(Exception):
    """Raised when a PDF cannot be opened or parsed (corrupt, encrypted, timed out)."""


class OcrError(Exception):
    """Raised when an OCR pass fails."""


class OcrUnavailable(OcrError):
    """Raised when the OCR engine or its system binaries are not installed."""
```

- [ ] **Step 3: Write `__init__.py` (will grow as tasks land)**

```python
"""trapezia-document-reader: generic PDF read + OCR primitives."""

from trapezia_document_reader.errors import (
    DocumentReadError,
    OcrError,
    OcrUnavailable,
)

__version__ = "0.1.0"

__all__ = ["DocumentReadError", "OcrError", "OcrUnavailable", "__version__"]
```

- [ ] **Step 4: Write the failing test `tests/test_errors.py`**

```python
from trapezia_document_reader import (
    DocumentReadError,
    OcrError,
    OcrUnavailable,
    __version__,
)


def test_error_hierarchy():
    assert issubclass(OcrUnavailable, OcrError)
    assert issubclass(DocumentReadError, Exception)


def test_version_exposed():
    assert __version__ == "0.1.0"
```

- [ ] **Step 5: Install editable + run test**

Run: `pip install -e ".[dev]"` then `pytest tests/test_errors.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git init && git add -A && git commit -m "feat: project scaffold + errors module"
```

---

## Task 2: Synthetic PHI-free fixture builder

**Files:**
- Create: `tests/fixtures/build_fixtures.py`
- Create: `tests/conftest.py`
- Generated/committed: `tests/fixtures/{born_digital_columnar,ruled_table,scanned_stub}.pdf`

- [ ] **Step 1: Write `tests/fixtures/build_fixtures.py`**

```python
"""Generate deterministic, PHI-free sample PDFs for tests.

Run once: `python tests/fixtures/build_fixtures.py`. Output committed.
NO real provider/patient data — invented analytes and values only.
"""
from pathlib import Path

from PIL import Image, ImageDraw
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

HERE = Path(__file__).parent
ROWS = [
    ("Widget", "12.0", "g/dL", "10.0-15.0"),
    ("Gadget", "4.5", "mmol", "3.0-5.0"),
    ("Sprocket", "99", "U/L", "0-120"),
]


def born_digital_columnar(path: Path) -> None:
    """Whitespace-aligned columns, no ruled lines (LabCorp archetype)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Courier", 11)
    y = 720
    c.drawString(72, y, "Test       Result   Units   Reference")
    for name, val, unit, ref in ROWS:
        y -= 18
        c.drawString(72, y, f"{name:<11}{val:<9}{unit:<8}{ref}")
    c.showPage()
    c.save()


def ruled_table(path: Path) -> None:
    """A bordered grid so page.lines is populated (Quest ruled archetype)."""
    c = canvas.Canvas(str(path), pagesize=letter)
    c.setFont("Helvetica", 11)
    xs = [72, 200, 300, 380, 500]
    top, rowh = 720, 22
    nrows = len(ROWS) + 1
    for i in range(nrows + 1):
        c.line(xs[0], top - i * rowh, xs[-1], top - i * rowh)
    for x in xs:
        c.line(x, top, x, top - nrows * rowh)
    header = ["Test", "Result", "Units", "Reference"]
    data = [header] + [list(r) for r in ROWS]
    for ri, row in enumerate(data):
        y = top - ri * rowh - 15
        for ci, cell in enumerate(row):
            c.drawString(xs[ci] + 4, y, cell)
    c.showPage()
    c.save()


def scanned_stub(path: Path) -> None:
    """Image-only PDF (no text layer) for is_scanned/OCR tests."""
    img = Image.new("RGB", (1000, 300), "white")
    d = ImageDraw.Draw(img)
    d.text((40, 40), "Widget 12.0 g/dL 10.0-15.0", fill="black")
    d.text((40, 90), "Gadget 4.5 mmol 3.0-5.0", fill="black")
    png = HERE / "_scanned_stub.png"
    img.save(png)
    c = canvas.Canvas(str(path), pagesize=letter)
    c.drawImage(str(png), 40, 400, width=520, height=156)
    c.showPage()
    c.save()
    png.unlink()


if __name__ == "__main__":
    born_digital_columnar(HERE / "born_digital_columnar.pdf")
    ruled_table(HERE / "ruled_table.pdf")
    scanned_stub(HERE / "scanned_stub.pdf")
    print("fixtures written to", HERE)
```

- [ ] **Step 2: Generate the fixtures**

Run: `python tests/fixtures/build_fixtures.py`
Expected: prints `fixtures written to …` and 3 `.pdf` files exist.

- [ ] **Step 3: Write `tests/conftest.py`**

```python
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
```

- [ ] **Step 4: Commit**

```bash
git add -A && git commit -m "test: synthetic PHI-free PDF fixtures + builder"
```

---

## Task 3: `is_scanned` (scan.py)

**Files:**
- Create: `src/trapezia_document_reader/scan.py`
- Modify: `src/trapezia_document_reader/__init__.py`
- Test: `tests/test_scan.py`

- [ ] **Step 1: Write the failing test `tests/test_scan.py`**

```python
from trapezia_document_reader import is_scanned


def test_born_digital_is_not_scanned(columnar_pdf):
    assert is_scanned(columnar_pdf) is False


def test_image_only_is_scanned(scanned_pdf):
    assert is_scanned(scanned_pdf) is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_scan.py -v`
Expected: FAIL with `ImportError: cannot import name 'is_scanned'`.

- [ ] **Step 3: Write `scan.py`**

```python
"""Detect whether a PDF is a born-digital text PDF or an image-only scan."""
from pathlib import Path

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

SCANNED_TEXT_THRESHOLD = 50


def is_scanned(path: str | Path) -> bool:
    """Return True if page 0 has no real text layer but carries images.

    Cheap gate (opens page 0 only). Used to decide whether OCR must run
    before the page can be parsed.
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            if not pdf.pages:
                return False
            page = pdf.pages[0]
            text = page.extract_text() or ""
            has_images = bool(page.images)
    except Exception as exc:  # pdfplumber/pdfminer raise a variety of types
        raise DocumentReadError(f"cannot open {path}: {exc}") from exc
    return len(text.strip()) < SCANNED_TEXT_THRESHOLD and has_images
```

- [ ] **Step 4: Add to `__init__.py`**

Add `from trapezia_document_reader.scan import is_scanned` and append `"is_scanned"` to `__all__`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_scan.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: is_scanned gate"
```

---

## Task 4: `pdf_to_pages` (pages.py)

**Files:**
- Create: `src/trapezia_document_reader/pages.py`
- Modify: `src/trapezia_document_reader/__init__.py`
- Test: `tests/test_pages.py`

- [ ] **Step 1: Write the failing test `tests/test_pages.py`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_pages.py -v`
Expected: FAIL with `ImportError: cannot import name 'pdf_to_pages'`.

- [ ] **Step 3: Write `pages.py`**

```python
"""Turn a PDF into per-page text + geometry dicts (JSON-serializable)."""
from pathlib import Path
from typing import Any

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

PageDict = dict[str, Any]
_WORD_ATTRS = ["x0", "x1", "top", "bottom", "size"]


def _word(w: dict) -> dict:
    return {
        "text": w.get("text", ""),
        "x0": float(w["x0"]),
        "x1": float(w["x1"]),
        "top": float(w["top"]),
        "bottom": float(w["bottom"]),
        "size": float(w.get("size", 0.0)),
    }


def _line(ln: dict) -> dict:
    return {
        "x0": float(ln["x0"]),
        "x1": float(ln["x1"]),
        "top": float(ln["top"]),
        "bottom": float(ln["bottom"]),
    }


def pdf_to_pages(path: str | Path) -> list[PageDict]:
    """Return one dict per page: text, layout-text, word boxes, line segments.

    The dict is a superset that keeps simple consumers (which read only
    ``page["text"]`` / ``page["page"]``) working unchanged, while exposing
    word x-positions and ruled lines for table extraction.
    """
    out: list[PageDict] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                words = page.extract_words(extra_attrs=["size"]) or []
                out.append(
                    {
                        "page": i,
                        "text": page.extract_text() or "",
                        "text_layout": page.extract_text(layout=True) or "",
                        "words": [_word(w) for w in words],
                        "lines": [_line(ln) for ln in (page.lines or [])],
                    }
                )
    except DocumentReadError:
        raise
    except Exception as exc:
        raise DocumentReadError(f"cannot parse {path}: {exc}") from exc
    return out
```

- [ ] **Step 4: Add to `__init__.py`**

Add `from trapezia_document_reader.pages import pdf_to_pages, PageDict` and append `"pdf_to_pages"`, `"PageDict"` to `__all__`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_pages.py -v`
Expected: 2 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: pdf_to_pages adapter"
```

---

## Task 5: `extract_tables` — ruled strategy (tables.py)

**Files:**
- Create: `src/trapezia_document_reader/tables.py`
- Modify: `src/trapezia_document_reader/__init__.py`
- Test: `tests/test_tables_ruled.py`

- [ ] **Step 1: Write the failing test `tests/test_tables_ruled.py`**

```python
from trapezia_document_reader import extract_tables


def test_ruled_extracts_grid(ruled_pdf):
    tables = extract_tables(ruled_pdf, page_number=1, strategy="ruled")
    assert len(tables) == 1
    rows = tables[0]
    assert rows[0] == ["Test", "Result", "Units", "Reference"]
    assert ["Widget", "12.0", "g/dL", "10.0-15.0"] in rows
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tables_ruled.py -v`
Expected: FAIL with `ImportError: cannot import name 'extract_tables'`.

- [ ] **Step 3: Write `tables.py` (ruled only for now)**

```python
"""Generic table extraction: ruled grids and whitespace-columnar layouts.

Returns raw cell strings only — no header detection or semantic mapping.
"""
from pathlib import Path

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

Table = list[list[str]]


def _clean(rows) -> Table:
    out: Table = []
    for row in rows:
        out.append([(c or "").strip() for c in row])
    return out


def _ruled(page) -> list[Table]:
    settings = {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
    return [_clean(t) for t in (page.extract_tables(settings) or [])]


def extract_tables(
    path: str | Path,
    page_number: int,
    *,
    strategy: str = "auto",
    column_hints: list[float] | None = None,
) -> list[Table]:
    """Extract tables from one page (1-based).

    strategy: "ruled" (use page lines), "columnar" (whitespace bands),
    or "auto" (ruled if the page has lines, else columnar).
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            page = pdf.pages[page_number - 1]
            if strategy == "ruled":
                return _ruled(page)
            raise NotImplementedError(strategy)  # columnar/auto land in Task 6
    except (DocumentReadError, NotImplementedError):
        raise
    except Exception as exc:
        raise DocumentReadError(f"cannot extract tables from {path}: {exc}") from exc
```

- [ ] **Step 4: Add to `__init__.py`**

Add `from trapezia_document_reader.tables import extract_tables, Table` and append `"extract_tables"`, `"Table"` to `__all__`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_tables_ruled.py -v`
Expected: 1 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: extract_tables ruled strategy"
```

---

## Task 6: `extract_tables` — columnar + auto

**Files:**
- Modify: `src/trapezia_document_reader/tables.py`
- Test: `tests/test_tables_columnar.py`

- [ ] **Step 1: Write the failing test `tests/test_tables_columnar.py`**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_tables_columnar.py -v`
Expected: FAIL with `NotImplementedError: columnar`.

- [ ] **Step 3: Replace the body of `extract_tables` and add column-band helpers in `tables.py`**

Add these helpers above `extract_tables`:

```python
def _column_bands(words, tol: float = 12.0) -> list[float]:
    """Cluster word left-edges (x0) into columns; return vertical-line x-coords.

    Lines are placed midway between one column's rightmost x1 and the next
    column's leftmost x0, plus outer bounds.
    """
    if not words:
        return []
    starts = sorted(w["x0"] for w in words)
    clusters: list[list[float]] = [[starts[0]]]
    for x in starts[1:]:
        if x - clusters[-1][-1] <= tol:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    col_left = [min(c) for c in clusters]
    # rightmost x1 of any word belonging (by nearest start) to each column
    col_right = list(col_left)
    for w in words:
        ci = min(range(len(col_left)), key=lambda i: abs(w["x0"] - col_left[i]))
        col_right[ci] = max(col_right[ci], w["x1"])
    lines = [col_left[0] - 2.0]
    for i in range(len(col_left) - 1):
        lines.append((col_right[i] + col_left[i + 1]) / 2.0)
    lines.append(col_right[-1] + 2.0)
    return lines


def _columnar(page, column_hints: list[float] | None) -> list["Table"]:
    words = [
        {"x0": float(w["x0"]), "x1": float(w["x1"])}
        for w in (page.extract_words() or [])
    ]
    verticals = column_hints if column_hints else _column_bands(words)
    if len(verticals) < 2:
        return []
    settings = {
        "vertical_strategy": "explicit",
        "explicit_vertical_lines": verticals,
        "horizontal_strategy": "text",
    }
    return [_clean(t) for t in (page.extract_tables(settings) or [])]
```

Then replace the `if strategy == "ruled": ... raise NotImplementedError` block with:

```python
            if strategy == "ruled":
                return _ruled(page)
            if strategy == "columnar":
                return _columnar(page, column_hints)
            if strategy == "auto":
                return _ruled(page) if page.lines else _columnar(page, column_hints)
            raise ValueError(f"unknown strategy: {strategy}")
```

And update the `except (DocumentReadError, NotImplementedError):` line to `except (DocumentReadError, ValueError):`.

- [ ] **Step 4: Run both table test files**

Run: `pytest tests/test_tables_columnar.py tests/test_tables_ruled.py -v`
Expected: all passed.

- [ ] **Step 5: Commit**

```bash
git add -A && git commit -m "feat: extract_tables columnar band detection + auto"
```

---

## Task 7: `ocr_add_text_layer` (ocr.py)

**Files:**
- Create: `src/trapezia_document_reader/ocr.py`
- Modify: `src/trapezia_document_reader/__init__.py`
- Test: `tests/test_ocr.py`

- [ ] **Step 1: Write the failing test `tests/test_ocr.py`**

```python
import shutil

import pytest

from trapezia_document_reader import is_scanned, ocr_add_text_layer, pdf_to_pages

pytest.importorskip("ocrmypdf")
if shutil.which("tesseract") is None:
    pytest.skip("tesseract binary not installed", allow_module_level=True)


def test_ocr_makes_scanned_readable(scanned_pdf, tmp_path):
    assert is_scanned(scanned_pdf) is True
    out = ocr_add_text_layer(scanned_pdf, out_path=tmp_path / "ocr.pdf")
    assert out.exists()
    assert is_scanned(out) is False
    text = " ".join(p["text"] for p in pdf_to_pages(out))
    assert "Widget" in text
```

- [ ] **Step 2: Run test to verify it fails (or skips cleanly)**

Run: `pytest tests/test_ocr.py -v`
Expected: FAIL `ImportError: cannot import name 'ocr_add_text_layer'` when ocrmypdf+tesseract present; otherwise the module skips.

- [ ] **Step 3: Write `ocr.py`**

```python
"""Add a searchable text layer to a scanned PDF via ocrmypdf (out-of-process)."""
from pathlib import Path

from trapezia_document_reader.errors import OcrError, OcrUnavailable
from trapezia_document_reader.isolation import run_isolated


def _ocr_impl(src: str, dst: str, lang: str, force: bool) -> str:
    import ocrmypdf

    ocrmypdf.ocr(
        src,
        dst,
        language=lang,
        force_ocr=force,
        skip_text=not force,
        progress_bar=False,
    )
    return dst


def ocr_add_text_layer(
    path: str | Path,
    *,
    out_path: str | Path | None = None,
    lang: str = "eng",
    force: bool = False,
    timeout: int = 120,
) -> Path:
    """Return a NEW PDF with an invisible OCR text layer; input untouched.

    Idempotent: a PDF that already has text is passed through (``skip_text``)
    unless ``force``. Runs ocrmypdf in a worker process under ``timeout`` so a
    pathological scan can't hang the caller.
    """
    src = Path(path)
    dst = Path(out_path) if out_path else src.with_suffix(".ocr.pdf")
    try:
        import ocrmypdf  # noqa: F401
    except ImportError as exc:
        raise OcrUnavailable("ocrmypdf is not installed (pip install '.[ocr]')") from exc
    try:
        run_isolated(_ocr_impl, str(src), str(dst), lang, force, timeout=timeout)
    except Exception as exc:
        msg = str(exc).lower()
        if "tesseract" in msg or "ghostscript" in msg or "not found" in msg:
            raise OcrUnavailable(f"OCR system binary missing: {exc}") from exc
        raise OcrError(f"OCR failed for {src}: {exc}") from exc
    return dst
```

- [ ] **Step 4: Add to `__init__.py`**

Add `from trapezia_document_reader.ocr import ocr_add_text_layer` and append `"ocr_add_text_layer"` to `__all__`.

- [ ] **Step 5: Run test (depends on Task 8's `run_isolated`)**

Note: `ocr.py` imports `run_isolated` from `isolation.py` — **implement Task 8 first if executing strictly in order**, or temporarily inline a direct call. Run: `pytest tests/test_ocr.py -v`
Expected: 1 passed (or skipped if OCR toolchain absent).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: ocr_add_text_layer via ocrmypdf"
```

---

## Task 8: Out-of-process isolation (isolation.py)

> Implement before Task 7's run step (Task 7 depends on `run_isolated`). Listed after for narrative flow; reorder freely.

**Files:**
- Create: `src/trapezia_document_reader/isolation.py`
- Modify: `src/trapezia_document_reader/__init__.py`
- Test: `tests/test_isolation.py`

- [ ] **Step 1: Write the failing test `tests/test_isolation.py`**

```python
import time

import pytest

from trapezia_document_reader import DocumentReadError
from trapezia_document_reader.isolation import pdf_to_pages_isolated, run_isolated


def _add(a, b):
    return a + b


def _sleep(seconds):
    time.sleep(seconds)
    return "done"


def test_run_isolated_returns_value():
    assert run_isolated(_add, 2, 3, timeout=10) == 5


def test_run_isolated_times_out():
    with pytest.raises(DocumentReadError):
        run_isolated(_sleep, 5, timeout=1)


def test_pdf_to_pages_isolated(columnar_pdf):
    pages = pdf_to_pages_isolated(columnar_pdf, timeout=30)
    assert pages[0]["page"] == 1 and "Widget" in pages[0]["text"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_isolation.py -v`
Expected: FAIL `ImportError: cannot import name 'run_isolated'`.

- [ ] **Step 3: Write `isolation.py`**

```python
"""Run a heavy/risky call in a worker process under a wall-clock timeout.

pdfplumber parsing and OCR can hang or exhaust memory on pathological input;
isolating them keeps a long-lived caller (the salus daemon) alive.
"""
import multiprocessing as mp
from pathlib import Path
from typing import Any, Callable

from trapezia_document_reader.errors import DocumentReadError
from trapezia_document_reader.pages import pdf_to_pages

_CTX = mp.get_context("spawn")  # portable: Windows + Linux


def _worker(func, args, q):
    try:
        q.put(("ok", func(*args)))
    except Exception as exc:  # ship a plain string; exc may not pickle
        q.put(("err", f"{type(exc).__name__}: {exc}"))


def run_isolated(func: Callable[..., Any], *args: Any, timeout: float) -> Any:
    """Execute ``func(*args)`` in a spawned process; raise on timeout/crash.

    ``func`` must be importable at module scope (spawn pickles by reference).
    """
    q = _CTX.Queue()
    p = _CTX.Process(target=_worker, args=(func, args, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        raise DocumentReadError(f"isolated call timed out after {timeout}s")
    if q.empty():
        raise DocumentReadError(f"isolated call died (exit={p.exitcode})")
    status, payload = q.get()
    if status == "err":
        raise DocumentReadError(f"isolated call failed: {payload}")
    return payload


def pdf_to_pages_isolated(path: str | Path, *, timeout: float = 60) -> list[dict]:
    """`pdf_to_pages` run in a worker process under ``timeout``."""
    return run_isolated(pdf_to_pages, str(path), timeout=timeout)
```

- [ ] **Step 4: Add to `__init__.py`**

Add `from trapezia_document_reader.isolation import run_isolated, pdf_to_pages_isolated` and append both names to `__all__`.

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_isolation.py -v`
Expected: 3 passed.

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: run_isolated + pdf_to_pages_isolated"
```

---

## Task 9: `read_pdf` convenience (reader.py)

**Files:**
- Create: `src/trapezia_document_reader/reader.py`
- Modify: `src/trapezia_document_reader/__init__.py`
- Test: `tests/test_reader.py`

- [ ] **Step 1: Write the failing test `tests/test_reader.py`**

```python
from trapezia_document_reader import read_pdf


def test_born_digital_no_ocr(columnar_pdf):
    result = read_pdf(columnar_pdf, ocr="never")
    assert result["ocr_applied"] is False
    assert "Widget" in result["pages"][0]["text"]
    assert result["working_path"] == str(columnar_pdf)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_reader.py -v`
Expected: FAIL `ImportError: cannot import name 'read_pdf'`.

- [ ] **Step 3: Write `reader.py`**

```python
"""High-level convenience: OCR-if-needed, then return pages."""
from pathlib import Path
from typing import Any

from trapezia_document_reader.ocr import ocr_add_text_layer
from trapezia_document_reader.pages import pdf_to_pages
from trapezia_document_reader.scan import is_scanned


def read_pdf(
    path: str | Path,
    *,
    ocr: str = "auto",
    lang: str = "eng",
) -> dict[str, Any]:
    """Return ``{pages, ocr_applied, source_path, working_path}``.

    ocr: "auto" (OCR iff scanned), "always", or "never".
    """
    src = Path(path)
    do_ocr = ocr == "always" or (ocr == "auto" and is_scanned(src))
    working = ocr_add_text_layer(src, lang=lang) if do_ocr else src
    return {
        "pages": pdf_to_pages(working),
        "ocr_applied": bool(do_ocr),
        "source_path": str(src),
        "working_path": str(working),
    }
```

- [ ] **Step 4: Add to `__init__.py`**

Add `from trapezia_document_reader.reader import read_pdf` and append `"read_pdf"` to `__all__`.

- [ ] **Step 5: Run the full suite**

Run: `pytest -v`
Expected: all passed (OCR test skipped if toolchain absent).

- [ ] **Step 6: Commit**

```bash
git add -A && git commit -m "feat: read_pdf convenience"
```

---

## Task 10: Docs, README, release prep

**Files:**
- Create: `README.md`
- Create: `docs/conf.py`, `docs/index.rst`
- Test: `tests/test_public_api.py`

- [ ] **Step 1: Write `tests/test_public_api.py` (locks the v0.1.0 surface)**

```python
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
```

- [ ] **Step 2: Run it**

Run: `pytest tests/test_public_api.py -v`
Expected: PASS (fix any missing exports until green).

- [ ] **Step 3: Write `README.md`**

```markdown
# trapezia-document-reader

Generic, clinical-agnostic PDF read + OCR primitives for the Trapezia platform.
The read/ingest counterpart to `trapezia-document-writer` (markdown → PDF/DOCX/HTML).

## Install
    pip install trapezia-document-reader          # parsing only (pdfplumber)
    pip install "trapezia-document-reader[ocr]"   # + OCR (ocrmypdf; needs system tesseract + ghostscript)

## API
- `is_scanned(path)` — image-only scan vs born-digital
- `ocr_add_text_layer(path, ...)` — add a searchable text layer (ocrmypdf)
- `pdf_to_pages(path)` — per-page text + layout + word boxes + lines
- `extract_tables(path, page_number, strategy=...)` — ruled / columnar / auto; raw cells only
- `read_pdf(path, ocr="auto")` — OCR-if-needed then pages
- `run_isolated` / `pdf_to_pages_isolated` — bound heavy calls by timeout in a worker process

No clinical logic and no LLM: it returns text/geometry/cells; meaning is the consumer's job.
```

- [ ] **Step 4: Write minimal Sphinx config `docs/conf.py`**

```python
project = "trapezia-document-reader"
extensions = ["sphinx.ext.autodoc", "sphinx.ext.napoleon"]
html_theme = "alabaster"
autodoc_typehints = "description"
```

- [ ] **Step 5: Write `docs/index.rst`**

```rst
trapezia-document-reader
========================

.. automodule:: trapezia_document_reader.scan
   :members:
.. automodule:: trapezia_document_reader.pages
   :members:
.. automodule:: trapezia_document_reader.tables
   :members:
.. automodule:: trapezia_document_reader.ocr
   :members:
.. automodule:: trapezia_document_reader.reader
   :members:
.. automodule:: trapezia_document_reader.isolation
   :members:
```

- [ ] **Step 6: Full suite + tag**

Run: `pytest -v`
Expected: all green (OCR skipped if toolchain absent).

```bash
git add -A && git commit -m "docs: README + sphinx scaffold + public-api lock"
git tag v0.1.0
```

---

## Self-Review (completed against the spec)

- **Spec coverage:** is_scanned (T3), ocr_add_text_layer (T7), pdf_to_pages incl. `lines` (T4), extract_tables ruled+columnar+auto (T5–T6), read_pdf (T9), run_isolated/isolated variants (T8), dependency tiering + packaging (T1), synthetic PHI-free fixtures (T2), Sphinx docs + Google docstrings (T10). `Document` handle intentionally **out** per Decision 7.
- **Dependency note:** Task 7 (`ocr.py`) imports from Task 8 (`isolation.py`) — execute Task 8 before Task 7's run step (flagged in T7 Step 5).
- **Type consistency:** `PageDict` keys (`page/text/text_layout/words/lines`) consistent across T4/T6/T8; `Table = list[list[str]]` consistent T5/T6; `read_pdf` result keys match the spec contract.

## Out of scope (separate plans)
- Salus Slice 2 re-pointing to this lib + OCR pre-pass wiring → trapezia-salus plan ([#64]).
- Writer rename `trapezia-export-markdown` → `trapezia-document-writer` → its own small plan.

[#64]: https://github.com/OrionAIDev/trapezia-roadmap/issues/64
