# trapezia-document-reader — Design Spec

**Status:** draft · **Date:** 2026-06-18 · **Roadmap:** [#63] (this lib) · [#64] (salus OCR wiring) · relates salus [#49] (lab-PDF extractor), [#40], [#50]

## Context

Trapezia has a **write/render** side — `trapezia-export-markdown` (renaming to `trapezia-document-writer`) turns markdown → PDF/DOCX/HTML — but **no read/ingest** side. PDF *reading* is mid-flight inside `trapezia-salus/labs/extract/` ([#49] Slice 2): `pdf_pages.py` (pdfplumber adapter + `is_scanned()`) and per-vendor LabCorp/Quest extractors are being written, with the **generic table-geometry mechanics (column-band detection, ruled-table reads) currently coupled into the clinical vendor extractors**.

Real driver: the salus-family backlog probe (2026-06-16) found, of 64 PDFs — ~25 lab reports (20 whitespace-columnar, 5 ruled), **26 scanned/image-only needing OCR**, 13 narrative. OCR has no handler today; scanned PDFs are detected and quarantined `reason:"needs_ocr"`.

**Decisions locked with Chris (2026-06-18):** generic PDF mechanics lift to a platform library; clinical semantics stay in salus. Names follow the `trapezia-*` = engine-lib / `*-skill` = agent-wrapper convention. OCR engine = `ocrmypdf`. The reader lib is extracted **first**, and salus Slice 2 is built on top of it.

## Goal

A standalone, **clinical-agnostic**, pip-installable Python library that turns a PDF — born-digital **or** scanned — into **text + geometry + generic table rows**, so downstream consumers parse *domain semantics* without reimplementing PDF mechanics or OCR. Code-first per the dev principles; **no LLM in this lib** (the narrative-LLM tail stays in the consumer).

## Boundary — in vs. out

| In `trapezia-document-reader` (generic) | Stays in `trapezia-salus/labs/extract` (clinical) |
|---|---|
| `is_scanned()`, `ocr_add_text_layer()` | LabCorp/Quest **content** detection (header sniff) |
| `pdf_to_pages()` (text + layout + word boxes + lines) | LOINC code maps, column-synonym → canonical mapping |
| `extract_tables()` (ruled + whitespace-columnar band mechanics) | reference-range parsing (`<200`/`>=60`/`a-b`), interpretation flags |
| `read_pdf()` convenience; out-of-process isolation | observation-dict schema, `domain` tagging, candidate adapter, router wiring, dedup keys |

Rule of thumb: the lib returns **raw cells and geometry**; it never decides what a column *means*.

## Public API / contracts

All functions are pure reads that **never mutate the input file**. Page data is plain JSON-serializable dicts (no pdfplumber objects leak across the boundary), so output can cross the daemon UDS or a subprocess boundary unchanged.

### 1. `pdf_to_pages(path) -> list[PageDict]`
pdfplumber-backed. `PageDict` is a **superset** of what the existing salus prior-provider extractors read (`page["text"]`, `page["page"]`) so they keep working unchanged:
```
PageDict = {
  "page":        int,            # 1-based
  "text":        str,            # extract_text()
  "text_layout": str,            # extract_text(layout=True) — preserves column alignment
  "words":       list[WordBox],  # extract_words(extra_attrs=["x0","x1","top","size"])
  "lines":       list[LineSeg],  # page.lines (for ruled-table detection)
}
WordBox = {"text": str, "x0": float, "x1": float, "top": float, "bottom": float, "size": float}
LineSeg = {"x0": float, "x1": float, "top": float, "bottom": float}
```
Raises `DocumentReadError` on unreadable/encrypted/corrupt input.

### 2. `is_scanned(path) -> bool`
Cheap gate (opens page 0 only): `extract_text()` shorter than `SCANNED_TEXT_THRESHOLD` (~50 chars) **and** image objects present → `True`. Used to decide whether OCR must run before parsing.

### 3. `ocr_add_text_layer(path, *, out_path=None, lang="eng", force=False, timeout=120) -> Path`
Wraps **`ocrmypdf`**. Produces a **new** PDF with an invisible searchable text layer behind the page images; input untouched. After it, `is_scanned()` returns `False` and `pdf_to_pages()`/`extract_tables()` work with **no other code path** — OCR is a *pre-pass*, not a parallel pipeline.
- Idempotent: a PDF that already has a text layer → `--skip-text` (or short-circuit) unless `force=True`.
- Runs out-of-process under `timeout` (ocrmypdf already shells to tesseract; we still bound it).
- Raises `OcrError` (OCR failed) / `OcrUnavailable` (tesseract binary missing).

### 4. `extract_tables(path, page_number, *, strategy="auto", column_hints=None) -> list[Table]`
`Table = list[Row]`, `Row = list[str]` (raw cell text only — **no header/semantic interpretation**). This is the geometry mechanics **lifted out of the salus vendor extractors**.
- `strategy="ruled"` — pdfplumber `extract_tables({"vertical_strategy":"lines",...})` when `page.lines` present.
- `strategy="columnar"` — derive column x-bands from the word x-position histogram → `explicit_vertical_lines` + `horizontal_strategy:"text"`. (Default `extract_tables()` fails on whitespace-aligned reports — proven: 51/64 returned no schema.)
- `strategy="auto"` — ruled if `page.lines` present, else columnar.
- `column_hints`: optional pre-computed x-band boundaries (lets a consumer reuse a column model across a multi-page table).

### 5. `read_pdf(path, *, ocr="auto", lang="eng") -> ReadResult`
Convenience composition of the pipeline:
```
ReadResult = {
  "pages":        list[PageDict],
  "ocr_applied":  bool,
  "source_path":  str,
  "working_path": str,   # == source_path unless OCR produced a new file
}
```
- `ocr="auto"` → run `ocr_add_text_layer` first iff `is_scanned`; `"always"` / `"never"` force the choice.

### 6. Out-of-process isolation — `run_isolated(callable, *args, timeout, rss_limit=None)`
pdfplumber parsing **and** OCR are the heavy/risky operations (a 64-PDF pdfplumber run has dropped an SSH session). The lib provides a `multiprocessing`-worker wrapper that runs a pure call in a child process under a wall-clock `timeout` and optional `rss_limit`; on timeout/crash it raises `DocumentReadError`/`OcrError` instead of hanging or OOM-ing the caller. Consumers that must stay alive (the salus daemon, single-writer) call the **isolated** variants (`pdf_to_pages_isolated`, etc.); in-process variants remain for trusted/small inputs and tests. Applies to the pdfplumber extractor too — **not** an OCR-only safeguard.

## Packaging

- **Repo:** `OrionAIDev/trapezia-document-reader` — **public** (recommended), like `trapezia-export-markdown`, so the salus-server Docker build can `pip install` from a git URL with no deploy key. No PHI ever lives here (synthetic fixtures only). *(Public vs private — open question below.)*
- **Distribution / import:** dist `trapezia-document-reader`; import `trapezia_document_reader`.
- **Dependency tiers (keep base light):**
  - base install → **pdfplumber only** (parsing + tables). Consumers that only read born-digital PDFs pull nothing heavy.
  - `pip install trapezia-document-reader[ocr]` → adds `ocrmypdf` (which pulls system **`tesseract`** + **`ghostscript`** — a Dockerfile concern for salus-server, not a pip dep). salus-server installs the `[ocr]` extra.
- **Layout:**
  ```
  src/trapezia_document_reader/{__init__,document,pages,scan,tables,ocr,isolation,errors}.py
  tests/  docs/(sphinx)  pyproject.toml
  ```
- **Python conventions** (trapezia-disciplines): Google-style docstrings always; **Sphinx autodoc applies** (this is a `~/dev/` package, not a skill).

## Testing / PHI

- **Synthetic, PHI-free fixtures only** — build deterministic sample PDFs with `reportlab`: born-digital whitespace-columnar, ruled-table, multi-column, and a **scanned stub** (render text → image → image-only PDF) for `is_scanned`/OCR. No real provider/patient data (public repo — doubly important; mirrors the salus CI phi-scan).
- Key assertions:
  - `is_scanned`: born-digital → False; scanned stub → True.
  - OCR round-trip: scanned stub → `ocr_add_text_layer` → `is_scanned` False → `pdf_to_pages` returns the known seeded text.
  - `extract_tables`: columnar + ruled fixtures → expected row/cell structure (raw strings).
  - isolation: a synthetic "hang"/oversize fixture trips `timeout` → raises, parent survives.

## Salus migration impact ([#49] Slice 2, separate plan in trapezia-salus)

- `salus/labs/extract/pdf_pages.py` is **removed**; salus imports `pdf_to_pages`/`is_scanned`/`extract_tables` from `trapezia_document_reader`.
- Band-detection/table mechanics being written into `labcorp.py`/`quest.py` are **replaced by `extract_tables()` calls**; the vendor extractors keep only column-synonym mapping + LOINC + ref-range + observation shape.
- The router's `needs_ocr` quarantine flips to an **OCR pre-pass** (`read_pdf(..., ocr="auto")`) once the `[ocr]` extra ships in the salus-server image.
- Update **Decision 4** of `trapezia-salus/docs/superpowers/specs/2026-06-16-salus-lab-pdf-extractor-design.md` to point at `trapezia-document-reader` (one-line edit).

## Slices (feeds the implementation plan)

- **S1** — repo scaffold + `pages` (`pdf_to_pages`) + `scan` (`is_scanned`) + reportlab fixtures + tests. Base deps only.
- **S2** — `tables` (`extract_tables`: ruled + columnar band strategy) + tests.
- **S3** — `ocr` (`ocr_add_text_layer` via ocrmypdf; `[ocr]` extra) + scanned fixture + round-trip test.
- **S4** — `isolation` (`run_isolated` + `*_isolated` variants + timeout/rss) + tests.
- **S5** — `read_pdf` convenience + Sphinx docs + **v0.1.0** tagged release. (Public `Document` handle **deferred** — see Decision 6; parse-once stays an internal detail.)
- **(salus, separate plan, Rule 8 for prod)** — re-point salus Slice 2 to the lib; wire OCR pre-pass; re-scan the 26 scanned + the lab PDFs.

## Decisions (Chris, 2026-06-18)

1. **Boundary** — generic mechanics → lib; clinical semantics → salus. ✓
2. **`extract_tables` lifts to the lib** (max clean cut; vendor extractors keep only semantics). ✓
3. **Sequencing** — extract the reader lib first; build salus Slice 2 on it; OCR pre-pass; isolation folded into router wiring; writer rename alongside. ✓
4. **OCR engine = `ocrmypdf`** — adds a text layer so downstream "just works"; needs system `tesseract` in the salus-server image. Switch to `rapidocr-onnxruntime` **only** if ocrmypdf proves insufficient (poor extraction) or too resource-heavy. ✓
5. **Naming** — libs `trapezia-document-reader` / `trapezia-document-writer`; OpenClaw wrappers `document-reader-skill` / `document-writer-skill` (cf. `salus-skill`). ✓
6. **Repo public** — simplest for the salus-server Docker pip-from-git step; no PHI ever (synthetic fixtures only). ✓
7. **`Document` handle deferred** — parse-once is an internal implementation detail; the public context-managed handle is non-breaking to add later, so it's YAGNI for v0.1.0. ✓

## Resolved (was open)

- Visibility → **public** (Decision 6). Roadmap → **[#63]** (lib) + **[#64]** (salus OCR wiring) created 2026-06-18. `Document` handle → **deferred** (Decision 7).

[#40]: https://github.com/OrionAIDev/trapezia-roadmap/issues/40
[#49]: https://github.com/OrionAIDev/trapezia-roadmap/issues/49
[#50]: https://github.com/OrionAIDev/trapezia-roadmap/issues/50
[#63]: https://github.com/OrionAIDev/trapezia-roadmap/issues/63
[#64]: https://github.com/OrionAIDev/trapezia-roadmap/issues/64
