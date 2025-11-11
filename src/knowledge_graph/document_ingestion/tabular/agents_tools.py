"""Agent-aware CSV tools used by both agent and pipeline steps.

These functions centralize CSV sniffing and safe reading so that the
pipeline and agent code paths share consistent behavior and logging.
"""

from __future__ import annotations

import csv
import os
import logging
from typing import List, Tuple, Optional


logger = logging.getLogger("knowledgeAgent.tabular.tools")


# --- Logging helpers (preview controls) ---
# Enable previews when either:
#  - logger is set to DEBUG, or
#  - env KG_TOOLS_LOG_PREVIEW is truthy (1/true/yes/on)
def _env_truthy(name: str) -> bool:
    v = os.getenv(name)
    return bool(v) and str(v).strip().lower() in {"1", "true", "yes", "on"}


_PREVIEW_ENABLED_ENV = _env_truthy("KG_TOOLS_LOG_PREVIEW")
_PREVIEW_ROWS = int(os.getenv("KG_TOOLS_PREVIEW_ROWS", "5") or 5)
_PREVIEW_COLS = int(os.getenv("KG_TOOLS_PREVIEW_COLS", "10") or 10)
_PREVIEW_CELL_MAX = int(os.getenv("KG_TOOLS_PREVIEW_CELL_MAXLEN", "80") or 80)
_PREVIEW_STR_MAX = int(os.getenv("KG_TOOLS_PREVIEW_STR_MAX", "1024") or 1024)


def _should_log_preview() -> bool:
    try:
        return _PREVIEW_ENABLED_ENV or logger.isEnabledFor(logging.DEBUG)
    except Exception:
        return False


def _truncate_cell(x: Optional[str], max_len: int) -> str:
    s = "" if x is None else str(x)
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + "…"


def _render_csv_preview(headers: List[str], rows: List[List[str]], delimiter: str,
                        *, max_rows: int = _PREVIEW_ROWS, max_cols: int = _PREVIEW_COLS, max_cell: int = _PREVIEW_CELL_MAX) -> str:
    try:
        cols = min(len(headers), max_cols)
        # Render header line
        head = delimiter.join(_truncate_cell(h, max_cell) for h in headers[:cols])
        # Render up to N rows
        out = [f"Headers ({len(headers)}): {head}"]
        for i, r in enumerate(rows[: max_rows]):
            cell_count = min(len(r), cols)
            line = delimiter.join(_truncate_cell(v, max_cell) for v in r[:cell_count])
            out.append(f"Row {i+1}: {line}")
        if len(rows) > max_rows:
            out.append(f"… (+{len(rows) - max_rows} more preview rows omitted)")
        return "\n".join(out)
    except Exception as exc:
        return f"<preview render failed: {exc}>"


def _emit_preview(header: str, body: str) -> None:
    """Emit preview text at INFO if env-enabled, otherwise DEBUG."""
    try:
        fn = logger.info if _PREVIEW_ENABLED_ENV else logger.debug
        fn("%s\n%s", header, body)
    except Exception:
        # Don't break the caller for logging failures
        pass


def sniff_csv(path: str, sample_size: int = 2048, *, delimiter: Optional[str] = None):
    """Detect a CSV delimiter using a small sample.

    Returns a simple value representing the delimiter (a string), instead of
    defining a csv.Dialect subclass. This keeps usage simple and avoids scope
    issues in class bodies.
    """
    logger.info("[tools] sniff_csv start path=%s sample_size=%d", path, sample_size)
    if not os.path.exists(path):
        raise FileNotFoundError(f"File not found: {path}")
    if delimiter:
        delim = delimiter
    else:
        with open(path, "r", encoding="utf-8", newline="") as f:
            sample = f.read(sample_size)
            f.seek(0)
            sniffer_choice = None
            try:
                sniffer_choice = csv.Sniffer().sniff(sample)
            except Exception:
                sniffer_choice = None
            # Log a short, sanitized snippet of the sample for debugging
            if _should_log_preview():
                try:
                    snippet = (sample or "")[: _PREVIEW_STR_MAX]
                    safe = snippet.replace("\r", "\\r").replace("\n", "\\n")
                    _emit_preview("[tools] sniff_csv sample (first %d chars): %s" % (len(snippet), safe), "")
                except Exception:
                    pass
            # Try candidates and pick the most stable by column count across first N rows
            candidates = [',', '\t', ';', '|']
            best = (',', -1)
            for d in candidates:
                # Score this delimiter by consistency of columns across first ~50 rows
                f.seek(0)
                reader = csv.reader(f, delimiter=d)
                cols = []
                try:
                    for i, row in enumerate(reader):
                        cols.append(len(row))
                        if i >= 50:
                            break
                except Exception:
                    cols = []
                score = 0
                if cols:
                    from collections import Counter
                    c = Counter(cols)
                    mode_ct = max(c.values())
                    score = mode_ct  # higher is better
                if score > best[1]:
                    best = (d, score)
            # Compare sniffer vs best candidate; prefer best if it has a positive score
            if best[1] > 0:
                delim = best[0]
            else:
                delim = getattr(sniffer_choice, 'delimiter', None) or ','
    logger.info(
        "[tools] sniff_csv done delimiter='%s'",
        delim,
    )
    return delim


def read_rows(path: str, dialect, limit: int = 1000) -> List[List[str]]:
    """Read up to 'limit' rows using a provided dialect."""
    # Accept either a delimiter string or an object with a 'delimiter' attribute
    delim = dialect if isinstance(dialect, str) else (getattr(dialect, "delimiter", ",") or ",")
    logger.info(
        "[tools] read_rows start path=%s delimiter='%s' limit=%d",
        path,
        delim,
        limit,
    )
    rows: List[List[str]] = []
    with open(path, "r", encoding="utf-8", newline="") as f:
        reader = csv.reader(f, delimiter=delim)
        for i, row in enumerate(reader):
            rows.append(row)
            if i >= limit:
                break
    logger.info("[tools] read_rows done rows_read=%d", len(rows))
    # Optionally log a compact preview of rows read
    if rows and _should_log_preview():
        try:
            headers = rows[0]
            data = rows[1:]
            # Use the same delimiter computed above
            preview = _render_csv_preview(headers, data, delim)
            _emit_preview("[tools] csv preview from read_rows:", preview)
        except Exception:
            logger.debug("[tools] preview suppressed due to render error", exc_info=True)
    return rows


def read_headers_and_sample(path: str, sample_rows: int = 30, *, delimiter: Optional[str] = None) -> Tuple[List[str], List[List[str]], str]:
    """Convenience: returns (headers, data_rows_sample, delimiter)."""
    logger.info("[tools] read_headers_and_sample start path=%s sample_rows=%d", path, sample_rows)
    delim = sniff_csv(path, delimiter=delimiter)
    rows = read_rows(path, delim, limit=sample_rows + 1)
    if not rows:
        logger.warning("[tools] read_headers_and_sample: empty CSV")
        return [], [], (delim or ",")
    headers = rows[0]
    data = rows[1:]
    logger.info(
        "[tools] read_headers_and_sample done columns=%d rows_sampled=%d delimiter='%s'",
        len(headers),
        len(data),
        delim,
    )
    # Log a focused preview of headers and first few data rows
    if _should_log_preview():
        try:
            preview = _render_csv_preview(headers, data, delim)
            _emit_preview("[tools] csv preview (headers + sample):", preview)
        except Exception:
            logger.debug("[tools] preview suppressed due to render error", exc_info=True)
    return headers, data, delim


__all__ = [
    "sniff_csv",
    "read_rows",
    "read_headers_and_sample",
]
