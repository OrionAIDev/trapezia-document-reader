"""Run a heavy/risky call in a worker process under a wall-clock timeout.

pdfplumber parsing and OCR can hang or exhaust memory on pathological input;
isolating them keeps a long-lived caller (the salus daemon) alive.
"""
import multiprocessing as mp
import queue as _queue
from pathlib import Path
from typing import Any, Callable

from trapezia_document_reader.errors import DocumentReadError
from trapezia_document_reader.pages import PageDict, pdf_to_pages

_CTX = mp.get_context("spawn")  # portable: Windows + Linux


def _worker(func, args, q):
    try:
        q.put(("ok", func(*args)))
    except Exception as exc:  # ship a plain string; exc may not pickle
        q.put(("err", f"{type(exc).__name__}: {exc}"))


def run_isolated(func: Callable[..., Any], *args: Any, timeout: float) -> Any:
    """Execute ``func(*args)`` in a spawned process; raise on timeout/crash.

    ``func`` must be importable at module scope (spawn pickles by reference).
    The result is drained from the queue *before* joining the child: a child
    that has put a large object on the queue blocks until the pipe is read, so
    joining first would deadlock (and falsely time out) on large payloads.
    """
    q = _CTX.Queue()
    p = _CTX.Process(target=_worker, args=(func, args, q))
    p.start()
    try:
        status, payload = q.get(timeout=timeout)
    except _queue.Empty:
        p.terminate()
        p.join()
        raise DocumentReadError(f"isolated call timed out after {timeout}s")
    p.join()
    if status == "err":
        raise DocumentReadError(f"isolated call failed: {payload}")
    return payload


def pdf_to_pages_isolated(path: str | Path, *, timeout: float = 60) -> list[PageDict]:
    """`pdf_to_pages` run in a worker process under ``timeout``."""
    return run_isolated(pdf_to_pages, str(path), timeout=timeout)
