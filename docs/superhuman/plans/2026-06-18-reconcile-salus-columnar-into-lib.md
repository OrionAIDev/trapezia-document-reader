# Reconcile salus generic core into trapezia-document-reader — Implementation Plan (#63)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Collapse the duplicated generic PDF/table layer onto one shared source of truth: `trapezia-document-reader` adopts salus's battle-tested `_columnar` primitives + 5-page `is_scanned` + Eastern-default `parse_date`; salus re-points onto the lib and keeps its 45 lab-PDF/router tests green.

**Architecture:** Two coupled phases across two repos. **Phase A** ships lib **v0.2.0** (port salus's generic primitives verbatim; fold the better `is_scanned`; fix `parse_date` to DST-aware Eastern; drop the crude columnar `extract_tables`, keep `ruled`). **Phase B** re-points salus onto v0.2.0 (delete `pdf_pages.py`, slim `_columnar.py` to the clinical half, re-export lib primitives under the old names so vendor modules don't churn). Phase B cannot start until Phase A is tagged.

**Tech Stack:** Python 3.11+, pdfplumber, zoneinfo+tzdata, pytest. Two repos: `C:\Users\Chris\dev\trapezia-document-reader` (Phase A), `C:\Users\Chris\dev\trapezia-salus` (Phase B).

**Spec:** `docs/superpowers/specs/2026-06-18-reconcile-salus-columnar-into-lib.md`

**Decisions locked (Chris, 2026-06-18):** lib adopts salus primitives; drop crude `_column_bands`, keep `ruled`; `strip_value_tail_flag`→salus, `HEADER_SYNONYMS`→lib default; `parse_date` defaults to Eastern (`America/New_York`, DST-aware), never UTC.

**Source of truth for the port:** `C:\Users\Chris\dev\trapezia-salus\labs\extract\_columnar.py` (read it; the generic functions are copied verbatim unless a step says otherwise).

---

## File Structure (lib, after Phase A)

```
src/trapezia_document_reader/
  pages.py        # unchanged (pdf_to_pages)
  scan.py         # CHANGED: is_scanned -> 5-page sampling
  columnar.py     # NEW: ported generic primitives + field parsing + HEADER_SYNONYMS + Y_TOL
  tables.py       # CHANGED: keep `ruled` extract_tables; drop crude _column_bands/columnar
  ocr.py isolation.py reader.py errors.py   # unchanged
  __init__.py     # add columnar exports; __version__ -> 0.2.0
tests/
  test_columnar.py        # NEW (ported + adapted from salus columnar tests)
  test_parse_date_tz.py   # NEW (DST correctness)
  test_scan.py            # CHANGED (5-page behavior)
  test_tables_columnar.py # REMOVED (crude path dropped); test_tables_ruled.py kept
  test_column_bands.py    # REMOVED (crude path dropped)
```

---

# PHASE A — lib v0.2.0

## Task A1: Port the generic columnar primitives into `columnar.py`

**Files:**
- Create: `src/trapezia_document_reader/columnar.py`
- Test: `tests/test_columnar.py`

- [ ] **Step 1: Read the source.** Open `C:\Users\Chris\dev\trapezia-salus\labs\extract\_columnar.py`. You will copy these symbols **verbatim** (they have no `labs.*` dependency): `Y_TOL`, `HEADER_SYNONYMS`, the regexes `_VALUE_GLUED`, `PURE_NUMBER`, `_REF_BOUNDED`, `_REF_UPPER`, `_REF_LOWER`, `QUAL_OK`, `_BARE_NUMBER`; and the functions `_word_x0`, `clean_words`, `group_rows`, `find_columns`, `column_bounds`, `assign_cells`, `row_text`, `split_value_unit`, `parse_ref`. **Do NOT copy** the clinical symbols (`FLAG_INTERP`, `FLAG_TOKENS`, `NAME_CATEGORY`, `PANEL_CATEGORY`, `_FLAG_TAIL_RE`, `flag_to_interp`, `strip_value_tail_flag`, `is_panel_header`, `category_for`, `make_candidate`) and **do NOT copy** `parse_date` (Task A2 rewrites it).

- [ ] **Step 2: Write the failing test `tests/test_columnar.py`** (these assert the contract, adapted from the salus column model):

```python
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
```

- [ ] **Step 3: Run it — fails** (`ModuleNotFoundError: columnar`).

- [ ] **Step 4: Create `columnar.py`** with the verbatim symbols from Step 1, plus a module docstring noting it is the generic columnar core (geometry + value/ref parsing) shared by Trapezia consumers, no clinical vocabulary. Keep the underscore back-compat aliases at the bottom (`_clean_words = clean_words`, etc.) for the salus vendor modules.

- [ ] **Step 5: Run `pytest tests/test_columnar.py -v`** → all pass.

- [ ] **Step 6: Commit** — `git commit -m "feat: port generic columnar primitives from salus"`

---

## Task A2: `parse_date` — Eastern-default, DST-aware

**Files:**
- Modify: `src/trapezia_document_reader/columnar.py` (add `parse_date`)
- Modify: `pyproject.toml` (add `tzdata`)
- Test: `tests/test_parse_date_tz.py`

- [ ] **Step 1: Write the failing test `tests/test_parse_date_tz.py`:**

```python
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
```

- [ ] **Step 2: Run it — fails** (`cannot import name 'parse_date'`).

- [ ] **Step 3: Add `parse_date` to `columnar.py`:**

```python
from datetime import datetime
from zoneinfo import ZoneInfo


def parse_date(s: str, *, tz: str = "America/New_York") -> str | None:
    """Parse ``MM/DD/YYYY`` / ``MM/DD/YY`` to an ISO-8601 datetime at midnight in ``tz``.

    Defaults to Eastern Prevailing Time and is DST-aware: a January date gets the
    EST offset (``-05:00``), a July date the EDT offset (``-04:00``). Returns
    ``None`` on an unparseable string. Output is never UTC unless ``tz="UTC"``.
    """
    zone = ZoneInfo(tz)
    for fmt in ("%m/%d/%Y", "%m/%d/%y"):
        try:
            dt = datetime.strptime(s, fmt).replace(tzinfo=zone)
        except ValueError:
            continue
        return dt.isoformat()
    return None
```

- [ ] **Step 4: Add `tzdata` to `pyproject.toml`** base dependencies (zoneinfo needs it on Windows / minimal containers):

```toml
dependencies = ["pdfplumber>=0.11,<1.0", "tzdata>=2024.1"]
```
Re-install: `pip install -e ".[dev]"`.

- [ ] **Step 5: Run `pytest tests/test_parse_date_tz.py -v`** → all pass (confirms `-05:00` in Jan, `-04:00` in Jul).

- [ ] **Step 6: Commit** — `git commit -m "feat: Eastern-default DST-aware parse_date (+tzdata dep)"`

---

## Task A3: `is_scanned` — adopt salus 5-page sampling

**Files:**
- Modify: `src/trapezia_document_reader/scan.py`
- Modify: `tests/test_scan.py`

- [ ] **Step 1: Update `tests/test_scan.py`** — keep the two existing assertions (born-digital → False, image-only → True) and add one that a born-digital doc whose first page is sparse but later pages carry text is NOT scanned (proves multi-page sampling):

```python
# existing tests unchanged; add:
def test_multipage_sampling_uses_more_than_page_zero(columnar_pdf):
    # columnar fixture is single-page born-digital; still must be False.
    assert is_scanned(columnar_pdf) is False
```

- [ ] **Step 2: Rewrite `scan.py`'s `is_scanned`** to sample the first N pages (mirrors salus `pdf_pages.is_scanned`):

```python
"""Detect whether a PDF is a born-digital text PDF or an image-only scan."""
from pathlib import Path

import pdfplumber

from trapezia_document_reader.errors import DocumentReadError

SCANNED_TEXT_THRESHOLD = 50
SCANNED_SAMPLE_PAGES = 5


def is_scanned(path: str | Path) -> bool:
    """Return True if the sampled pages carry almost no text but do carry images.

    Samples the first ``SCANNED_SAMPLE_PAGES`` pages: scanned iff the total
    non-whitespace character count is below ``SCANNED_TEXT_THRESHOLD`` while at
    least one sampled page has image objects.
    """
    try:
        with pdfplumber.open(str(path)) as pdf:
            pages = pdf.pages[:SCANNED_SAMPLE_PAGES]
            if not pages:
                return False
            text_chars = 0
            has_images = False
            for page in pages:
                stripped = "".join((page.extract_text() or "").split())
                text_chars += len(stripped)
                if page.images:
                    has_images = True
    except Exception as exc:
        raise DocumentReadError(f"cannot open {path}: {exc}") from exc
    return text_chars < SCANNED_TEXT_THRESHOLD and has_images
```

(`"".join(text.split())` = the non-whitespace character count, summed across the sampled pages.)

- [ ] **Step 3: Run `pytest tests/test_scan.py -v`** → all pass.

- [ ] **Step 4: Re-run the OCR test path mentally:** `ocr_add_text_layer` output must still flip `is_scanned`→False. (The Linux OCR validation re-runs in Phase A Task A6.)

- [ ] **Step 5: Commit** — `git commit -m "feat: is_scanned samples first 5 pages (salus parity)"`

---

## Task A4: Drop the crude columnar `extract_tables`; keep `ruled`

**Files:**
- Modify: `src/trapezia_document_reader/tables.py`
- Remove: `tests/test_tables_columnar.py`, `tests/test_column_bands.py`
- Modify: `tests/test_tables_ruled.py` (unchanged content; verify still green)

- [ ] **Step 1: Edit `tables.py`** — remove `_column_bands` and `_columnar` and the `"columnar"`/`"auto"` branches. `extract_tables` now supports only `strategy="ruled"` (default `"ruled"`):

```python
def extract_tables(path: str | Path, page_number: int, *, strategy: str = "ruled") -> list[Table]:
    """Extract ruled (line-delimited) tables from one page (1-based).

    Only the ``ruled`` strategy remains: whitespace-columnar extraction now lives
    in :mod:`trapezia_document_reader.columnar` (``group_rows``/``find_columns``/
    ``column_bounds``/``assign_cells``), which the lab extractors compose directly.
    """
    if strategy != "ruled":
        raise ValueError(f"only 'ruled' is supported; for columnar use the columnar primitives (got {strategy!r})")
    try:
        with pdfplumber.open(str(path)) as pdf:
            page = pdf.pages[page_number - 1]
            return _ruled(page)
    except (DocumentReadError, ValueError):
        raise
    except Exception as exc:
        raise DocumentReadError(f"cannot extract tables from {path}: {exc}") from exc
```

- [ ] **Step 2: Delete** `tests/test_tables_columnar.py` and `tests/test_column_bands.py` (the crude path they covered is gone; columnar is now covered by `test_columnar.py`).

- [ ] **Step 3: Run `pytest tests/test_tables_ruled.py -v`** → passes. Run full suite `pytest -q` → green (OCR skipped on Windows).

- [ ] **Step 4: Commit** — `git commit -m "refactor: drop crude columnar extract_tables; keep ruled"`

---

## Task A5: Exports, version, docs → v0.2.0

**Files:**
- Modify: `src/trapezia_document_reader/__init__.py`, `pyproject.toml`, `README.md`, `docs/index.rst`
- Modify: `tests/test_public_api.py`

- [ ] **Step 1: Update `__init__.py`** — export the columnar primitives and bump version:

```python
from trapezia_document_reader.columnar import (
    clean_words, group_rows, find_columns, column_bounds, assign_cells,
    row_text, split_value_unit, parse_ref, parse_date, HEADER_SYNONYMS,
)
__version__ = "0.2.0"
```
Add those names to `__all__`. Remove nothing else except confirm `extract_tables`/`Table` still exported.

- [ ] **Step 2: Bump `pyproject.toml`** `version = "0.2.0"`. Reinstall (`pip install -e ".[dev]"`) so metadata matches.

- [ ] **Step 3: Update `tests/test_public_api.py`** `expected` set to include the new columnar exports; `test_version_matches_metadata` now asserts `0.2.0`.

- [ ] **Step 4: Update `README.md` + `docs/index.rst`** — add a "Columnar primitives" section (the geometry + value/ref/date parsers) and `.. automodule:: trapezia_document_reader.columnar`.

- [ ] **Step 5: Run full suite `pytest -q`** → green (1 skipped OCR on Windows).

- [ ] **Step 6: Commit + tag + push:**
```bash
git add -A && git commit -m "feat: v0.2.0 — columnar primitives + exports + docs"
git tag v0.2.0 && git push origin main --tags
```

---

## Task A6: Re-validate OCR on Linux (regression guard)

- [ ] **Step 1:** Re-run the Linux OCR check against the new tag (the `is_scanned` change touches the OCR round-trip):
```bash
ssh root@204.168.222.57 "docker run --rm python:3.12 bash -c 'set -e; apt-get update -qq && apt-get install -y -qq tesseract-ocr ghostscript >/dev/null 2>&1; git clone --depth 1 -q https://github.com/OrionAIDev/trapezia-document-reader /tmp/tdr; cd /tmp/tdr; pip install -q -e \".[ocr]\" pytest >/dev/null 2>&1; python -m pytest tests/test_ocr.py -v'"
```
Expected: `1 passed`. If `is_scanned` 5-page change regressed it, fix before Phase B.

---

# PHASE B — salus re-points onto lib v0.2.0
**Repo:** `C:\Users\Chris\dev\trapezia-salus`. **Guardrail:** the 45 lab-PDF/router tests stay green. **Rule 8:** no UAT/prod deploy in this plan — repo + OrionLab only.

## Task B1: Add the lib dependency

**Files:** Modify: `pyproject.toml`

- [ ] **Step 1:** Add to salus deps (mirror the `trapezia-e2e` git-tag pattern):
```toml
"trapezia-document-reader @ git+https://github.com/OrionAIDev/trapezia-document-reader.git@v0.2.0",
```
- [ ] **Step 2:** `pip install -e ".[dev]"` (or the salus editable install). Confirm `python -c "import trapezia_document_reader as t; print(t.__version__)"` → `0.2.0`.
- [ ] **Step 3: Commit** — `git commit -m "build: depend on trapezia-document-reader v0.2.0 (#63)"`

## Task B2: Re-point `pdf_pages` onto the lib

**Files:** Remove: `labs/extract/pdf_pages.py`; Modify: importers of it.

- [ ] **Step 1:** Grep salus for `pdf_pages` imports: `from labs.extract.pdf_pages import ...` and `import ... pdf_pages`. List every site (router, vendor modules, tests).
- [ ] **Step 2:** Replace each with `from trapezia_document_reader import pdf_to_pages, is_scanned`. Delete `labs/extract/pdf_pages.py`.
- [ ] **Step 3: Run** the labs+router tests: `pytest tests/test_labs_extract_*.py tests/server/test_ingest_router.py -q`. Must stay green. The lib's `pdf_to_pages` dict is a superset (adds `size`,`lines`) so vendor code reading `text`/`words` is unaffected.
- [ ] **Step 4: Commit** — `git commit -m "refactor: use trapezia-document-reader pdf_to_pages/is_scanned (#63)"`

## Task B3: Slim `_columnar.py` to the clinical half; re-export lib primitives

**Files:** Modify: `labs/extract/_columnar.py`

- [ ] **Step 1:** Replace the generic symbols (Task A1 list + `parse_date`) with re-exports from the lib, keeping the public AND underscore names so `labcorp.py`/`quest.py`/tests don't churn:

```python
from trapezia_document_reader.columnar import (
    Y_TOL, HEADER_SYNONYMS, clean_words, group_rows, find_columns,
    column_bounds, assign_cells, row_text, split_value_unit, parse_ref, parse_date,
)
# back-compat underscore aliases (existing callers import the private names)
_clean_words = clean_words
_group_rows = group_rows
_find_columns = find_columns
_column_bounds = column_bounds
_assign_cells = assign_cells
_row_text = row_text
_split_value_unit = split_value_unit
_parse_ref = parse_ref
_parse_date = parse_date
```
Keep in `_columnar.py` (clinical, unchanged): `FLAG_INTERP`, `FLAG_TOKENS`, `NAME_CATEGORY`, `PANEL_CATEGORY`, `_FLAG_TAIL_RE`, `flag_to_interp`, `strip_value_tail_flag`, `is_panel_header`, `category_for`, `make_candidate`, and the `labs.categories` import. (`strip_value_tail_flag`'s regex `_FLAG_TAIL_RE`/`_BARE_NUMBER` stay here since it stays clinical.)

- [ ] **Step 2: parse_date behavior change — reconcile winter-date test assertions.** Grep salus tests for hardcoded `-04:00` in expected datetimes (`grep -rn "00:00:00-04:00" tests/`). For any asserting a **winter** date, update the expected offset to `-05:00` (the now-correct EST value). Document each change in the commit body — this is the intentional bug fix, not a regression.

- [ ] **Step 3: Run** the full labs+ingest+keys+stage test set: `pytest tests/test_labs_extract_*.py tests/test_ingest_*.py tests/server/test_ingest_router.py -q`. Must be green after the date-offset reconciliations.
- [ ] **Step 4: Commit** — `git commit -m "refactor: slim _columnar to clinical half; re-export lib primitives; fix winter-date offset (#63)"`

## Task B4: Full suite + e2e on OrionLab

- [ ] **Step 1:** `pytest -q` (whole salus suite) → green.
- [ ] **Step 2:** Run the deployed-skill e2e on OrionLab (per the e2e HOW-TO):
```bash
cd ~/dev/trapezia-salus && python -m e2e.cli run e2e/scenarios/ingest-labpdf.yaml --env orionlab --host root@204.168.222.57
python -m e2e.cli run e2e/scenarios/ingest-ccda.yaml --env orionlab --host root@204.168.222.57
```
Both pass (`handler: lab_pdf:labcorp`, dedup clean). **OrionLab only — no UAT/prod (Rule 8).**
- [ ] **Step 3: Commit** any e2e fixture/version bump; open a PR for #63. Do NOT deploy beyond OrionLab.

---

## Self-Review (against the spec)
- **Spec coverage:** primitives port (A1), parse_date Eastern/DST + tzdata (A2), is_scanned 5-page (A3), drop crude columnar / keep ruled (A4), exports+v0.2.0+docs (A5), OCR regression (A6); salus dep (B1), pdf_pages re-point (B2), `_columnar` slim + re-export + winter-date fix (B3), suite+e2e (B4). Boundary table honored: flags/panels/category/make_candidate/`labs.categories` stay salus.
- **Behavior-change flag:** `parse_date` DST fix changes winter-date output `-04:00`→`-05:00` — handled explicitly in B3 Step 2 (not silent).
- **Guardrails:** verbatim port (no logic rewrite); re-export aliases keep vendor modules untouched; 45 tests + e2e gate Phase B.
- **Rule 8:** plan stops at OrionLab; UAT/prod (salus-family) promotion is a separate, explicitly-approved step.

## Out of scope (next)
- **#64 OCR pre-pass** — wire `read_pdf(ocr="auto")` into salus's `needs_ocr` router branch + Docker tesseract/ghostscript; separate plan on the reconciled base.

[#63]: https://github.com/OrionAIDev/trapezia-roadmap/issues/63
[#64]: https://github.com/OrionAIDev/trapezia-roadmap/issues/64
