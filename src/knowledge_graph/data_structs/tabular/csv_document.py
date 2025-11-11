from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from .csv_profile import CSVProfile
from ..document import Document, DocumentMetadata


@dataclass
class CSVDocument:
    """Tabular-focused companion object for CSV datasets.

    This does not replace the canonical Document used by persistence. Instead,
    it captures CSV-specific semantics (delimiter, headers, sample rows, profile)
    and can be converted into a minimal Document to pass through the pipeline.
    """

    id: str
    file_path: str
    filename: str
    file_type: str = ".csv"
    file_size: int = 0
    title: str = ""

    # CSV-specific fields
    delimiter: str = ","
    encoding: str = "utf-8"
    headers: List[str] = field(default_factory=list)
    headers_normalized: List[str] = field(default_factory=list)
    sample_rows: List[List[str]] = field(default_factory=list)

    profile: Optional[CSVProfile] = None


    def to_document(self) -> Document:
        """Return a minimal canonical Document (raw/clean left empty)."""
        meta = self.metadata or DocumentMetadata(
            document_id=self.id,
            title=self.title or self.filename,
        )
        return Document(
            id=self.id,
            filename=self.filename,
            file_path=self.file_path,
            file_type=self.file_type,
            file_size=self.file_size,
            title=self.title or self.filename,
            raw_content="",
            clean_content="",
            metadata="",
            textChunks=[],
        )

    def show_summary_of_contents(self, max_rows: int = 5, max_cols: int = 10) -> str:
        """Produce a human-readable preview using cached headers/sample rows."""
        try:
            cols = min(len(self.headers), max_cols) if self.headers else 0
            head = self.delimiter.join((self.headers or [])[:cols])
            lines = [f"Headers ({len(self.headers)}): {head}"] if self.headers else []
            for i, r in enumerate(self.sample_rows[:max_rows]):
                row = self.delimiter.join(str(v) for v in (r[:cols] if cols else r))
                lines.append(f"Row {i+1}: {row}")
            return "\n".join(lines)
        except Exception:
            return "<no preview>"

