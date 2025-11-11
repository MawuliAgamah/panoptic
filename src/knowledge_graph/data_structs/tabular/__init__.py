"""Dataclasses and types for tabular (CSV) ingestion."""

from .csv_profile import CSVProfile, ColumnStat
from .csv_document import CSVDocument

__all__ = [
    "CSVProfile",
    "ColumnStat",
    "CSVDocument",
]
