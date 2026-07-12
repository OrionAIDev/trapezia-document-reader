"""Ported from trapezia-document-converter's vendored divergences (roadmap #118).

Debian bookworm ships Ghostscript 10.0.0, which ocrmypdf refuses to use with
``--skip-text``/``--redo-ocr`` (a known corruption regression). Without a
fallback, OCR of *any* scanned PDF dies on that host. These tests pin the
behaviour that ``_ocr_impl`` retries with ``force_ocr=True`` when — and only
when — it hits that Ghostscript guard, and that ``read_pdf`` threads an OCR
``timeout`` through to ``ocr_add_text_layer``.

The gs-guard cases mock ``ocrmypdf`` so they run without the binary or
tesseract installed (unlike the round-trip tests in ``test_ocr.py``).
"""

import sys
import types

import pytest

import trapezia_document_reader.ocr as ocr_mod
import trapezia_document_reader.reader as reader_mod
from trapezia_document_reader.errors import OcrError, OcrUnavailable

GS10_MSG = (
    "Ghostscript 10.0.0 through 10.02.0 (your version: 10.0.0) contain serious "
    "regressions that corrupt PDFs with existing text, such as those processed "
    "using --skip-text or --redo-ocr. Please upgrade, or use --force-ocr to "
    "discard existing text."
)


class _FakeOcrmypdf(types.ModuleType):
    """Stand-in for the ocrmypdf module recording each ``ocr()`` call."""

    def __init__(self, on_call):
        super().__init__("ocrmypdf")
        self.calls = []
        self._on_call = on_call

    def ocr(self, src, dst, **kwargs):  # noqa: D401 - mirrors ocrmypdf.ocr
        self.calls.append(kwargs)
        self._on_call(dst, kwargs)


@pytest.fixture
def fake_ocrmypdf(monkeypatch):
    def _install(on_call):
        fake = _FakeOcrmypdf(on_call)
        monkeypatch.setitem(sys.modules, "ocrmypdf", fake)
        return fake

    return _install


def _write(dst, _kwargs):
    with open(dst, "w", encoding="utf-8") as fh:
        fh.write("ocr'd")


def test_gs10_guard_triggers_force_ocr_fallback(fake_ocrmypdf, tmp_path):
    """skip_text blocked by the gs-10 guard → retried with force_ocr=True."""

    def on_call(dst, kwargs):
        if kwargs.get("skip_text"):  # the lossless first attempt
            raise RuntimeError(GS10_MSG)
        _write(dst, kwargs)  # force_ocr retry succeeds

    fake = fake_ocrmypdf(on_call)
    dst = tmp_path / "out.pdf"
    result = ocr_mod._ocr_impl(str(tmp_path / "in.pdf"), str(dst), "eng", False, {})

    assert result == str(dst)
    assert dst.exists()
    assert [c["force_ocr"] for c in fake.calls] == [False, True]  # tried skip, then force


def test_non_gs_error_is_not_retried(fake_ocrmypdf, tmp_path):
    """An unrelated failure propagates unchanged — no force-ocr masking."""

    def on_call(dst, kwargs):
        raise RuntimeError("some unrelated ocrmypdf explosion")

    fake = fake_ocrmypdf(on_call)
    with pytest.raises(RuntimeError, match="unrelated"):
        ocr_mod._ocr_impl(str(tmp_path / "in.pdf"), str(tmp_path / "o.pdf"), "eng", False, {})
    assert len(fake.calls) == 1  # no retry


def test_explicit_force_does_not_double_retry(fake_ocrmypdf, tmp_path):
    """If the caller already asked for force and it still hits the guard, re-raise."""

    def on_call(dst, kwargs):
        raise RuntimeError(GS10_MSG)

    fake = fake_ocrmypdf(on_call)
    with pytest.raises(RuntimeError, match="Ghostscript"):
        ocr_mod._ocr_impl(str(tmp_path / "in.pdf"), str(tmp_path / "o.pdf"), "eng", True, {})
    assert len(fake.calls) == 1  # already forced; no second attempt


def test_default_ocr_timeout_is_600():
    """Force-ocr re-OCRs every page, so the default ceiling was raised 120 → 600."""
    assert ocr_mod.DEFAULT_OCR_TIMEOUT == 600


def test_ocr_add_text_layer_default_out_is_not_a_sibling(fake_ocrmypdf, monkeypatch, tmp_path):
    """out_path=None must write to a temp file, not next to a (maybe read-only) source."""
    # Bypass the real subprocess isolation: just run the target func in-process.
    monkeypatch.setattr(
        ocr_mod, "run_isolated", lambda func, *a, timeout: func(*a)
    )
    fake_ocrmypdf(_write)
    src = tmp_path / "src.pdf"
    src.write_text("pdf")
    out = ocr_mod.ocr_add_text_layer(src)  # no out_path
    assert out.exists()
    assert out.parent != src.parent  # temp dir, not the source dir


def test_read_pdf_threads_timeout_to_ocr(monkeypatch):
    """read_pdf(timeout=) is passed through to ocr_add_text_layer."""
    seen = {}

    def fake_ocr(path, **kwargs):
        seen.update(kwargs)
        return path

    monkeypatch.setattr(reader_mod, "is_scanned", lambda p: True)
    monkeypatch.setattr(reader_mod, "ocr_add_text_layer", fake_ocr)
    monkeypatch.setattr(reader_mod, "pdf_to_pages", lambda p: [{"text": "x"}])

    reader_mod.read_pdf("x.pdf", ocr="always", timeout=42)
    assert seen.get("timeout") == 42


def test_read_pdf_without_timeout_omits_it(monkeypatch):
    """No timeout → ocr_add_text_layer is called without a timeout kwarg (uses its default)."""
    seen = {}

    def fake_ocr(path, **kwargs):
        seen.update(kwargs)
        return path

    monkeypatch.setattr(reader_mod, "is_scanned", lambda p: True)
    monkeypatch.setattr(reader_mod, "ocr_add_text_layer", fake_ocr)
    monkeypatch.setattr(reader_mod, "pdf_to_pages", lambda p: [{"text": "x"}])

    reader_mod.read_pdf("x.pdf", ocr="always")
    assert "timeout" not in seen
