
"""CSV-specific load step to create a Document with minimal fields.

This is intentionally lightweight so you can run the pipeline end-to-end with
just a single step. It does not parse or chunk the CSV; it only constructs the
Document object with basic metadata filled in.
"""

from __future__ import annotations

import os
import logging

from ...document_pipeline import (
    DocumentPipelineContext,
    DocumentPipelineError,
    PipelineStep,
)
from ....data_structs.document import DocumentNew
from knowledge_graph.persistence.sqlite.sql_lite import SqlLite
from knowledge_graph.settings.settings import get_settings

logger = logging.getLogger("knowledgeAgent.pipeline.load_csv")


class LoadCSVStep(PipelineStep):
    """Create a Document instance for a CSV file and attach it to context."""

    name = "load_csv"

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        params = context.params
        file_path = params.document_path
        document_id = params.document_id
        kb_id = params.kb_id

        if not os.path.exists(file_path):
            raise DocumentPipelineError(f"File not found: {file_path}")

        file_size = os.path.getsize(file_path)
        filename = os.path.basename(file_path)
        title = os.path.splitext(filename)[0]

        # Convert document_id to integer (or None for auto-increment)
        doc_id_int = None
        if document_id:
            try:
                doc_id_int = int(document_id)
            except (ValueError, TypeError):
                # If document_id is a string like "doc_xxx", generate a consistent int
                doc_id_int = abs(hash(document_id)) % (10 ** 9)

        # Convert kb_id to integer (required, default to 0 if None/invalid)
        kb_id_int = 0
        if kb_id:
            try:
                kb_id_int = int(kb_id)
            except (ValueError, TypeError):
                if isinstance(kb_id, str):
                    try:
                        kb_id_int = int(kb_id)
                    except ValueError:
                        kb_id_int = abs(hash(kb_id)) % (10 ** 9)
                else:
                    kb_id_int = 0

        # Normalize file_type: remove leading dot and uppercase
        file_ext = os.path.splitext(filename)[1]  # Get extension with dot, e.g., ".csv"
        file_type_clean = file_ext.lstrip('.').upper() if file_ext else "CSV"  # "CSV"

        logger.info(f"Loading a CSV document {filename} into database with id {doc_id_int}")
        csv_doc = DocumentNew(
            id=doc_id_int,  # Integer or None
            ontology_id=None,  # Will be set later when ontology is created
            kb_id=kb_id_int,  # Integer, required
            file_name=filename,
            file_path=file_path,
            file_type=file_type_clean,  # "CSV" not ".csv"
            file_size=file_size,
            file_hash=None,
            status="pending",
            processed_at=None,  # Will be set when processing completes
        )

        sqlite = SqlLite(settings=get_settings())
        doc_repo = sqlite.document_repository()
        logger.info(f"Saving CSV document {csv_doc} to database")
        doc_repo.save_document(csv_doc)


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
