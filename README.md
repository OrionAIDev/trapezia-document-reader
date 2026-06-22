# trapezia-document-reader

Generic, clinical-agnostic PDF read + OCR primitives for the Trapezia platform.
The read/ingest counterpart to `trapezia-document-writer` (markdown → PDF/DOCX/HTML).

## Install
    pip install trapezia-document-reader          # parsing only (pdfplumber)
    pip install "trapezia-document-reader[ocr]"   # + OCR (ocrmypdf; needs system tesseract + ghostscript)

## Primary entry point
`read_pdf(path, ocr="auto")` is the recommended entry point for most callers — it
OCRs the document if needed, then returns its pages:

    from trapezia_document_reader import read_pdf
    result = read_pdf("report.pdf")            # ocr="auto": OCR only if scanned
    for page in result["pages"]:
        print(page["text"])

The remaining exports are lower-level primitives for advanced/explicit use:
- `is_scanned(path)` — image-only scan vs born-digital
- `ocr_add_text_layer(path, ...)` — add a searchable text layer (ocrmypdf)
- `pdf_to_pages(path)` — per-page text + layout + word boxes + lines
- `extract_tables(path, page_number, strategy=...)` — ruled table extraction; raw cells only
- `run_isolated` / `pdf_to_pages_isolated` — bound heavy calls by timeout in a worker process
- columnar primitives — `group_rows`/`find_columns`/`column_bounds`/`assign_cells` (table geometry), `split_value_unit`/`parse_ref`/`parse_date` (field parsing), `HEADER_SYNONYMS` (overridable column-name map)

### Columnar primitives

For ruleless, whitespace-aligned tables (no drawn lines), the columnar layer
reconstructs table geometry from word boxes: `clean_words` normalizes a page's
words, `group_rows` clusters them into rows, and `find_columns` / `column_bounds`
/ `assign_cells` infer column boundaries and bucket each word into a cell.
Field parsers turn raw cell text into structured values: `split_value_unit`
splits a measurement into `(value, unit, flag)`, `parse_ref` parses a reference
range, and `parse_date` normalizes a date string (defaulting to Eastern,
`America/New_York`, DST-aware). `HEADER_SYNONYMS` is an overridable map from
header-text variants to canonical column names.

No clinical logic and no LLM: it returns text/geometry/cells; meaning is the consumer's job.
