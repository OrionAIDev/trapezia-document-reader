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
