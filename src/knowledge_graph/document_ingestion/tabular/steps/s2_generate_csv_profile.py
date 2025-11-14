"""Build a lightweight CSVProfile (headers + delimiter + small sample).

Kept minimal so mapping/agent steps have reliable headers and delimiter
without doing heavy parsing at this stage.
"""

from __future__ import annotations

import logging
from typing import List

from ...document_pipeline import DocumentPipelineContext, PipelineStep
from ....data_structs.tabular import CSVProfile, ColumnStat
from ..agents_tools import sniff_csv, read_rows
from knowledge_graph.persistence.sqlite.sql_lite import SqlLite
from knowledge_graph.settings.settings import get_settings


logger = logging.getLogger("knowledgeAgent.pipeline.csv.profile")


class GenerateCsvProfileStep(PipelineStep):
    name = "generate_csv_profile"

    def __init__(self, *, sample_rows: int = 50, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self.sample_rows = sample_rows

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return self.enabled and context.document is not None

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        document = context.ensure_document()

        # Ensure document has an ID (should be set in previous step)
        if not hasattr(document, 'id') or document.id is None:
            logger.error("Document missing required ID. Cannot create CSV profile without document_id.")
            raise ValueError("Document must have an ID to create a CSV profile")

        # Detect delimiter and read a small sample (header + data rows)
        delim = sniff_csv(document.file_path)
        rows = read_rows(document.file_path, delim, limit=self.sample_rows + 1)
        headers: List[str] = rows[0] if rows else []
        data_rows: List[List[str]] = rows[1:] if rows else []

        profile = CSVProfile(
            document_id=document.id,  # Integer foreign key to documents table
            headers_original=headers,
            headers_normalized=[str(h).strip().lower() for h in headers],
            delimiter=delim or ",",
            encoding="utf-8",
            row_count_sampled=len(data_rows),
            column_count=len(headers),
            columns=[],  # keep minimal for now
            sample_rows=data_rows[: min(10, len(data_rows))],
            path_label=document.file_name,
        )
        sqlite = SqlLite(settings=get_settings())
        doc_repo = sqlite.tabular_document_repository()
        logger.info(f"Saving CSV profile for document_id={document.id} to database")
        success = doc_repo.save_csv_profile(profile)
        if not success:
            logger.error(f"Failed to save CSV profile for document_id={document.id}")
            raise ValueError(f"Failed to save CSV profile for document_id={document.id}")
        logger.info(f"CSV profile saved successfully for document_id={document.id}")

        setattr(context, "csv_profile", profile)
        context.results[self.name] = {
            "headers": len(headers),
            "rows_sampled": len(data_rows),
            "delimiter": profile.delimiter,
        }

        logger.info("%s: CSV profile built headers=%d rows_sampled=%d delim='%s'",
                    document.id, len(headers), len(data_rows), profile.delimiter)
        return context

