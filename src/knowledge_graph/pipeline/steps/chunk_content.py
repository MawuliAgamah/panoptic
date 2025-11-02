"""Step responsible for chunking the cleaned document."""

from __future__ import annotations

import logging

from ..document_pipeline import DocumentPipelineContext, PipelineStep
from ..utils import Chunker, PageLevelChunker


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

        # Determine effective chunker type.
        effective_chunker_type = self.chunker_type
        file_type = (getattr(document, "file_type", "") or "").lower()

        # Avoid sending PDFs/DOC/DOCX through the structured markdown chunker.
        if effective_chunker_type == "structured_markdown" and file_type in {".pdf", "pdf", ".doc", "doc", ".docx", "docx"}:
            logger.info("%s: overriding chunker_type to 'auto' for file type %s", document.id, file_type)
            effective_chunker_type = "auto"

        logger.info(
            "%s: chunking with type=%s size=%d overlap=%d file_type=%s",
            document.id,
            effective_chunker_type,
            self.chunk_size,
            self.chunk_overlap,
            file_type,
        )

        # Prefer page-level chunking for PDFs when auto/page_pdf requested
        used_page_level = False
        if file_type in {".pdf", "pdf"} and effective_chunker_type in {"auto", "page_pdf"}:
            used_page_level = True
            logger.info("%s: using page-level chunker (size=%d overlap=%d)", document.id, self.chunk_size, self.chunk_overlap)
            plc = PageLevelChunker(self.chunk_size, self.chunk_overlap)
            texts = plc.chunk_document_by_page(document)
            metas = plc.create_page_chunk_metadata(document, texts)
            text_chunks = plc.reconstruct_document(document, texts, metas)
            document.textChunks = text_chunks
            document.is_chunked = True
        else:
            document = chunk_document(
                document,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                chunker_type=effective_chunker_type,
            )
        context.set_document(document)
        chunk_count = len(document.textChunks or [])

        # Fallback: if no chunks produced, retry with recursive chunker
        result_summary = {
            "chunk_count": chunk_count,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "chunker_type": effective_chunker_type,
        }
        if used_page_level:
            result_summary["used_page_level"] = True
        if chunk_count == 0:
            logger.warning(
                "No chunks generated for %s with strategy '%s'; retrying with recursive splitter",
                document.id,
                effective_chunker_type,
            )
            # Fallback to generic recursive splitter
            document = chunk_document(
                document,
                chunk_size=self.chunk_size,
                chunk_overlap=self.chunk_overlap,
                chunker_type="recursive",
            )
            context.set_document(document)
            chunk_count = len(document.textChunks or [])
            result_summary.update({
                "chunk_count": chunk_count,
                "fallback": "recursive",
            })

        # Log chunk diagnostics
        if chunk_count > 0:
            lengths = [len(c.content or "") for c in (document.textChunks or [])]
            try:
                avg_len = sum(lengths) // len(lengths)
                min_len = min(lengths)
                max_len = max(lengths)
            except Exception:
                avg_len = min_len = max_len = 0
            preview = (document.textChunks[0].content or "")[:200].replace("\n", " ") if document.textChunks else ""
            logger.info(
                "%s: chunked into %d chunks (avg=%d min=%d max=%d). first_chunk: '%s'%s",
                document.id,
                chunk_count,
                avg_len,
                min_len,
                max_len,
                preview,
                "…" if len(preview) == 200 else "",
            )

        context.results[self.name] = result_summary
        return context
