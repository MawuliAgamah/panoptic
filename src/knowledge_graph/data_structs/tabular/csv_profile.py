from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime
import hashlib


@dataclass
class ColumnStat:
    """Lightweight per-column statistics for CSV profiling."""

    name: str
    non_null: int
    nulls: int
    distinct: int
    inferred_type: str
    example_values: List[str] = field(default_factory=list)


@dataclass
class CSVProfile:
    """A deterministic summary of a CSV used by pipeline steps and agents.

    Intentionally small: headers, a few sample rows, basic per-column stats,
    delimiter/encoding, and a stable fingerprint for caching.
    """

    headers_original: List[str]
    headers_normalized: List[str]
    delimiter: str
    encoding: str
    row_count_sampled: int
    column_count: int
    columns: List[ColumnStat]
    sample_rows: List[List[str]] = field(default_factory=list)
    path_label: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)

    def dataset_fingerprint(self) -> str:
        """Return a stable fingerprint derived from headers + sample + delimiter."""
        h = hashlib.sha1()
        try:
            h.update("|".join(self.headers_normalized).encode("utf-8", errors="ignore"))
            h.update(self.delimiter.encode("utf-8", errors="ignore"))
            for row in self.sample_rows[:20]:  # cap to keep stable and small
                h.update("|".join(row).encode("utf-8", errors="ignore"))
        except Exception:
            pass
        return h.hexdigest()[:16]

