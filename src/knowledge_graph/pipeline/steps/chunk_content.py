"""Step responsible for chunking the cleaned document."""

from __future__ import annotations

import logging

from ..document_pipeline import DocumentPipelineContext, PipelineStep
from ..utils import Chunker


logger = logging.getLogger("knowledgeAgent.pipeline.chunk")


def chunk_document(
    document,
    *,
    chunk_size: int,
    chunk_overlap: int,
    chunker_type: str,
):
    chunker = Chunker(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunker_type=chunker_type,
    )

    logger.debug(
        "Chunking document %s with size=%d overlap=%d strategy=%s",
        document.id,
        chunk_size,
        chunk_overlap,
        chunker_type,
    )

    chunks = chunker.chunk_document(document)
    chunk_metadatas = chunker.create_chunk_metadata(document, chunks)
    text_chunks = chunker.reconstruct_document(document, chunks, chunk_metadatas)

    document.textChunks = text_chunks
    document.is_chunked = True

    logger.debug("Document %s chunked into %d chunks", document.id, len(text_chunks))
    return document


class ChunkContentStep(PipelineStep):
    """Generate structured chunks and associated metadata."""

    name = "chunk_content"

    def __init__(
        self,
        *,
        chunk_size: int,
        chunk_overlap: int,
        chunker_type: str,
    ) -> None:
        super().__init__(enabled=True)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker_type = chunker_type

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        # Only run when routing decided to use chunk-level processing
        route_info = context.results.get("route_document", {})
        route = route_info.get("route")
        if route != "chunk":
            logger.debug("Skipping chunking for route '%s'", route or "unknown")
            context.results[self.name] = {"chunk_count": 0, "skipped": True}
            return context

        document = context.ensure_document()
        document = chunk_document(
            document,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            chunker_type=self.chunker_type,
        )
        context.set_document(document)
        chunk_count = len(document.textChunks or [])
        context.results[self.name] = {
            "chunk_count": chunk_count,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
        }
        if chunk_count == 0:
            logger.info("No chunks generated for document %s", document.id)
        return context
