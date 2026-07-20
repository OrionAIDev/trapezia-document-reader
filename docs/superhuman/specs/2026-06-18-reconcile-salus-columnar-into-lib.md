# Reconcile salus `labs/extract` generic core into trapezia-document-reader (#63)

**Status:** draft — needs Chris sign-off on the central decision · **Date:** 2026-06-18 · **Roadmap:** [#63] · then [#64] (OCR) · **Repos:** `trapezia-document-reader` (gains primitives → v0.2.0) + `trapezia-salus` (re-points, stays at parity)

## Context — why this exists

Salus **v0.10.0** already shipped #49 **Slice 2** (`git 6972194`: LabCorp+Quest extractors wired into the router) and Slice 1 (#113 router). 45 salus lab-PDF/router tests pass. So there is **no "build Slice 2"** — it's done. What we have instead is **duplication**: salus independently built the same generic PDF/table machinery we just shipped in `trapezia-document-reader` v0.1.0.

Both sides built it *deliberately portable*. salus's `labs/extract/_columnar.py` docstring: *"intentionally Salus-light… so the columnar core stays portable."* Our spec kept `pages.py` dependency-light "to lift into a future lib." They converged — independently — on the same boundary. Now we collapse the two copies into one shared layer (the lib) so there is a single source of truth, and so OCR (#64) has a clean home.

| Generic capability | lib v0.1.0 | salus v0.10.0 |
|---|---|---|
| `pdf_to_pages` | `pages.py` ({page,text,text_layout,words+size,lines}) | `labs/extract/pdf_pages.py` ({page,text,text_layout,words} — no size/lines) |
| `is_scanned` | `scan.py` (page-0 sample) | `labs/extract/pdf_pages.py` (**5-page** sample, thr 50) |
| columnar table geometry | `tables.py` (`extract_tables` + crude `_column_bands`) | `labs/extract/_columnar.py` (rich primitives: group_rows/find_columns/column_bounds/assign_cells/…) |
| OCR pre-pass | `ocr.py` ✓ | — (router quarantines `needs_ocr`) |

## Central decision (needs Chris) — **lib adopts salus's generic primitives**

**Recommendation: the lib adopts salus's `_columnar` *generic* primitives; our speculative `extract_tables`/`_column_bands` is replaced by them.** Rationale:
- salus's primitives are **battle-tested against the real column model** (LabCorp/Quest, 45 passing tests) and are what the **actual consumer** (the vendor extractors) calls. Our `extract_tables(path, page)→rows` was designed speculatively *before* we knew Slice 2 existed; the real extractors don't want coarse rows, they compose fine-grained primitives (`group_rows → find_columns → column_bounds → assign_cells`).
- Keeping our coarser API and forcing salus onto it would be a **downgrade** of working code. Keeping both is the duplication we're trying to kill.
- This reshapes the lib's table layer → **lib goes to v0.2.0** (the `extract_tables` surface from v0.1.0 changes). Acceptable: v0.1.0 has exactly one consumer (none in prod yet) and was never released as stable beyond this session.

The alternative (salus keeps `_columnar`, lib only lends `pdf_pages`+OCR) leaves the table geometry duplicated forever and defeats the single-shared-layer goal. **Recommend against.**

## Function-by-function disposition (the crux)

The cut follows the project rule *generic mechanics → lib, clinical semantics → salus*. salus's `_columnar.py` straddles it; here's every symbol:

| Symbol (salus `_columnar.py`) | Goes to | Why |
|---|---|---|
| `clean_words`, `group_rows`, `find_columns`, `column_bounds`, `assign_cells`, `row_text`, `Y_TOL` | **lib** | pure word/row/column geometry — zero clinical knowledge, no `labs.*` import |
| `split_value_unit` | **lib** | generic "13.2g/dL" → (value, unit) numeric parsing |
| `parse_ref` | **lib** | generic range parse `a-b`/`<x`/`>=x` → {low,high,text} |
| `parse_date` | **lib** (Eastern default) | generic date parse with a **DST-aware default tz `America/New_York` (Eastern Prevailing Time)**, overridable via a `tz=` param. **Fixes a latent bug**: salus currently hardcodes `-04:00` (EDT) for every date, so winter (EST `-05:00`) dates are stamped with the wrong offset. zoneinfo gives the correct per-date offset. Output never lands in UTC. |
| `HEADER_SYNONYMS` | **lib** (as overridable default) | column-name synonyms; `find_columns` already takes a `synonyms=` override |
| `flag_to_interp`, `strip_value_tail_flag`, `FLAG_INTERP`, `FLAG_TOKENS` | **salus** | interpreting `H/HH/L/LL/*` as high/critical/abnormal is **clinical** lab semantics |
| `is_panel_header`, `PANEL_CATEGORY` | **salus** | CBC/CMP/lipid panel lexicon = clinical vocabulary |
| `category_for`, `NAME_CATEGORY` | **salus** | depends on `labs.categories.is_valid`; clinical taxonomy |
| `make_candidate` | **salus** | builds the clinical observation/candidate schema (`code.loinc`, `reference_range`, `interpretation`, `category`) |

Net: the lib gains a **generic columnar/table module** (geometry + value/ref/date parsing + synonym default). salus keeps a slimmed clinical module (flags, panels, categories, `make_candidate`, `labs.categories`). The vendor extractors (`labcorp.py`, `quest.py`) import geometry from the lib and clinical glue from salus.

> Borderline calls to confirm: `strip_value_tail_flag` (tangled — it strips a *clinical* flag token but is invoked during geometry; recommend **salus**, lib stays flag-agnostic). `HEADER_SYNONYMS` home.
>
> **Timezone (Chris, 2026-06-18):** dates default to **Eastern Prevailing Time** (`America/New_York`, DST-aware) — clinicians + output documents are all Eastern; never UTC. Implemented as `parse_date(s, *, tz="America/New_York")` using `zoneinfo`. This adds **`tzdata`** as a lib runtime dependency (zoneinfo has no system tz database on Windows / minimal Linux containers). A future org-wide tz config could relocate the default, but Eastern-as-lib-default is the simplest correct choice now.

## `is_scanned` / `pdf_to_pages` reconciliation
- **`is_scanned`** — adopt salus's **5-page sample** (more robust than the lib's page-0-only) into the lib; make the sample count a constant. Lib's `scan.py` changes; behavior-superset.
- **`pdf_to_pages`** — the lib's dict is already a **superset** of salus's (adds `size`, `lines`). salus extractors read only `text`/`words` x0/x1 → they keep working unchanged. salus deletes its `pdf_pages.py` and imports the lib's.

## `extract_tables` disposition
The lib's v0.1.0 `extract_tables(path, page, strategy)` + `_column_bands` are **superseded** by the adopted primitives. Options: (a) **drop** them (no consumer), or (b) keep `extract_tables` as a thin convenience layered over `find_columns`/`column_bounds`/`assign_cells`. Recommend **(a) drop** for now (YAGNI; re-add if a real consumer wants coarse rows). The `ruled` strategy (pdfplumber `lines`) has no salus equivalent and is genuinely useful — **keep `ruled` extraction**, drop only the crude columnar `_column_bands`.

## Migration sequence (keep 45 salus tests green throughout)
1. **lib v0.2.0** — add the generic columnar module (port the salus primitives verbatim — they're already clean), fold 5-page `is_scanned`, drop crude `_column_bands` (keep `ruled`). Port salus's primitive tests too. Tag v0.2.0, push.
2. **salus re-point** — bump the `trapezia-document-reader` git-dep to v0.2.0; delete `pdf_pages.py`; slim `_columnar.py` to the clinical half (re-export the lib's primitives under the old names so `labcorp.py`/`quest.py` imports don't churn — the existing `_clean_words = clean_words` alias pattern makes this trivial). Run the 45 tests — must stay green.
3. **verify** — full salus suite + the `ingest-labpdf`/`ingest-ccda` e2e on OrionLab.
4. **then #64 OCR** — separate, on the reconciled base.

## Risks
- Refactoring **working, merged, prod-adjacent** code (salus-family is production PHI). Mitigation: the 45 tests + e2e are the guardrail; re-export aliases keep the vendor modules untouched; lib ports the primitives *verbatim* (no behavior change), so this is a move, not a rewrite.
- Reshaping the lib's table API right after v0.1.0 — acceptable (no external consumers yet).

## Open decisions for Chris
1. **Confirm the central decision** — lib adopts salus's primitives (recommended), vs salus keeps `_columnar`.
2. **`extract_tables` v0.1.0 surface** — drop the crude columnar path (recommended) vs keep as a convenience wrapper.
3. **Borderline homes** — `strip_value_tail_flag`→salus, `HEADER_SYNONYMS`→lib-default per the table (recommended), or adjust. (`parse_date` → lib with Eastern/`America/New_York` DST-aware default — **decided** by Chris 2026-06-18.)

[#63]: https://github.com/OrionAIDev/trapezia-roadmap/issues/63
[#64]: https://github.com/OrionAIDev/trapezia-roadmap/issues/64
