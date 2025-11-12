"""Logging context utilities for injecting document/run IDs into log records."""

from __future__ import annotations

import logging
import contextvars
from typing import Optional

# Context variables to carry correlation IDs across the pipeline execution
_doc_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("doc_id", default="-")
_run_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("run_id", default="-")

class InjectContextFilter(logging.Filter):
    """Logging filter that injects document and run IDs into every record."""

    def filter(self, record: logging.LogRecord) -> bool:  # type: ignore[override]
        # Attach correlation fields if missing so formatters can include them safely
        if not hasattr(record, "doc_id"):
            try:
                record.doc_id = _doc_id_var.get()
            except Exception:
                record.doc_id = "-"
        if not hasattr(record, "run_id"):
            try:
                record.run_id = _run_id_var.get()
            except Exception:
                record.run_id = "-"
        return True


def set_logging_context(doc_id: Optional[str], run_id: Optional[str]) -> None:
    """Set logging correlation context for current execution."""
    _doc_id_var.set(doc_id or "-")
    _run_id_var.set(run_id or "-")


def clear_logging_context() -> None:
    """Clear logging correlation context."""
    _doc_id_var.set("-")
    _run_id_var.set("-")

