"""Step responsible for loading raw document content and initial metadata."""

from __future__ import annotations

import logging
import os
import uuid

from ..document_pipeline import (
    DocumentPipelineContext,
    DocumentPipelineError,
    PipelineStep,
)
from ...document.models.document import Document
from ...document.models.metadata import DocumentMetadata
from ..utils import ParserFactory


logger = logging.getLogger("knowledgeAgent.pipeline.load")


class DocumentLoadError(Exception):
    """Raised when a document cannot be loaded from disk."""


def load_document_from_path(document_path: str, document_id: str) -> Document:
    """Create a Document populated with raw content and metadata."""
    if not os.path.exists(document_path):
        raise DocumentLoadError(f"File not found: {document_path}")

    file_size = os.path.getsize(document_path)
    filename = os.path.basename(document_path)
    title = os.path.splitext(filename)[0]

    metadata = DocumentMetadata(
        title=title,
        document_id=document_id,
        metadata_id=str(uuid.uuid4()),
    )

    document = Document(
        id=document_id,
        filename=filename,
        file_path=document_path,
        file_type=os.path.splitext(document_path)[1],
        file_size=file_size,
        title=title,
        raw_content="",
        clean_content="",
        metadata=metadata,
        textChunks=[],
    )

    parser = ParserFactory.get_parser(document.file_type)
    raw_content = parser.parse(document.file_path)
    document.raw_content = raw_content
    document.is_parsed = True

    logger.debug("Loaded document %s (%d bytes)", document.id, len(raw_content))
    return document


class LoadDocumentStep(PipelineStep):
    """Create the Document instance and populate core metadata."""

    name = "load_document"

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        params = context.params

        try:
            document = load_document_from_path(params.document_path, params.document_id)
        except DocumentLoadError as exc:
            raise DocumentPipelineError(str(exc)) from exc

        # Ensure metadata container exists before attaching domain/tags.
        metadata = document.metadata or DocumentMetadata(document_id=document.id)

        # Preserve existing categories/tags while appending inputs.
        domain = params.domain
        tags = params.tags or []

        if domain and domain not in metadata.categories:
            metadata.categories.append(domain)

        for tag in tags:
            if tag not in metadata.tags:
                metadata.tags.append(tag)

        document.metadata = metadata
        context.set_document(document)
        return context
