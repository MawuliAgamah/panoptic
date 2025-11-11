
"""CSV-specific load step to create a Document with minimal fields.

This is intentionally lightweight so you can run the pipeline end-to-end with
just a single step. It does not parse or chunk the CSV; it only constructs the
Document object with basic metadata filled in.
"""

from __future__ import annotations

import os
import uuid
import logging

from ...document_pipeline import (
    DocumentPipelineContext,
    DocumentPipelineError,
    PipelineStep,
)
from ....data_structs.document import Document, DocumentMetadata
from ....data_structs.tabular import CSVDocument


logger = logging.getLogger("knowledgeAgent.pipeline.load_csv")


class LoadCSVStep(PipelineStep):
    """Create a Document instance for a CSV file and attach it to context."""

    name = "load_csv"

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        params = context.params
        file_path = params.document_path
        document_id = params.document_id or str(uuid.uuid4())

        if not os.path.exists(file_path):
            raise DocumentPipelineError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]


        # Build CSVDocument companion (no parsing yet)
        csv_doc = CSVDocument(
            id=document_id,
            file_path=file_path,
            filename=filename,
            file_type=".csv",
            file_size=file_size,
            title=title,
            delimiter=",",
            encoding="utf-8",
        )



        # Attach and record summary
        context.set_document(csv_doc)
        # Also expose the CSVDocument on context for tabular-aware steps
        setattr(context, "csv_document", csv_doc)
        context.results[self.name] = {
            "file": file_path,
            "document_id": document_id,
            "size_bytes": file_size,
            "type": csv_doc.file_type,
        }
        logger.info("Loaded CSV document %s (%d bytes)", filename, file_size)
        return context
