"""Step that coordinates knowledge graph extraction."""

from __future__ import annotations

import logging
from datetime import datetime

from typing import Optional

from ...document_pipeline import DocumentPipelineContext, PipelineStep
from .clean_content import clean_document_content
from .chunk_content import chunk_document


logger = logging.getLogger("knowledgeAgent.pipeline.kg")


def extract_knowledge_graph_for_document(
    document,
    kg_service,
    *,
    strategy: str,
    chunk_count: Optional[int] = None,
):
    if not kg_service:
        logger.warning("Knowledge graph service unavailable; skipping KG extraction")
        return document

    if not document.clean_content and document.raw_content:
        clean_document_content(document)

    if not document.validate_content_for_kg():
        logger.info("Document %s not suitable for KG extraction", document.id)
        document.is_kg_extracted = True
        document.knowledge_graph = {"entities": set(), "relations": []}
        return document

    if strategy == "document":
        result = kg_service.extract_from_document(document)
    elif strategy == "chunk":
        chunks = [chunk for chunk in (document.textChunks or []) if (chunk.content or "").strip()]
        if not chunks:
            logger.warning("Route was 'chunk' but no chunks available for %s", document.id)
            result = {"entities": set(), "relations": []}
        else:
            # Build per-chunk context using page_number when available
            texts = [c.content for c in chunks]
            contexts = []
            total_pages = getattr(getattr(document, 'metadata', None), 'num_pages', None)
            from collections import Counter
            page_counter = Counter()
            for i, c in enumerate(chunks):
                page = getattr(c.metadata, 'page_number', None)
                if page is not None:
                    page_counter[page] += 1
                    if total_pages:
                        ctx = f"Page {page} of {total_pages} | {document.title}"
                    else:
                        ctx = f"Page {page} | {document.title}"
                else:
                    ctx = f"Chunk {i+1} | {document.title}"
                contexts.append(ctx)

            # Log a brief context preview and per-page distribution for debugging
            try:
                preview_n = min(3, len(contexts))
                for j in range(preview_n):
                    logger.info("%s: chunk %d context: %s", document.id, j + 1, contexts[j])
                if page_counter:
                    # show up to first 5 pages in sorted order
                    top_pages = sorted(page_counter.items())[:5]
                    logger.info("%s: page distribution (first %d): %s", document.id, len(top_pages), top_pages)
            except Exception:
                pass

            result = kg_service.extract_from_chunks(texts, document.id, contexts=contexts)
        document.knowledge_graph = result
        document.is_kg_extracted = True
        document.kg_extracted_at = datetime.now()
        document.kg_extraction_metadata = {
            "strategy_used": "chunk-level",
            "chunk_count": len(chunks) if chunks else 0,
            "entity_count": len(result.get("entities", set())),
            "relation_count": len(result.get("relations", [])),
        }
    else:
        # Skip route: already handled above, but ensure fields are set
        result = {"entities": set(), "relations": []}
        document.knowledge_graph = result
        document.is_kg_extracted = True

    entities = result.get("entities", set())
    relations = result.get("relations", [])
    logger.debug(
        "Extracted KG for %s: entities=%d relations=%d",
        document.id,
        len(entities) if isinstance(entities, (set, list, tuple)) else 0,
        len(relations) if isinstance(relations, (set, list, tuple)) else 0,
    )
    return document


class ExtractKnowledgeGraphStep(PipelineStep):
    """Run KG extraction through the existing document manager logic."""

    name = "extract_knowledge_graph"

    def __init__(
        self,
        *,
        enabled: bool = True,
        chunk_size: int,
        chunk_overlap: int,
        chunker_type: str,
    ) -> None:
        super().__init__(enabled=enabled)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker_type = chunker_type

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        if not self.should_run(context):
            return context

        document = context.ensure_document()
        # If a prior step (e.g., CSV) has already produced a knowledge graph, skip LLM extraction
        pre_kg = getattr(document, "knowledge_graph", None) or {}
        if pre_kg.get("entities") or pre_kg.get("relations"):
            logger.info("%s: skipping LLM KG extraction; knowledge_graph already present", document.id)
            context.results[self.name] = {
                "skipped": True,
                "reason": "preexisting_kg",
                "entity_count": len(pre_kg.get("entities", [])),
                "relation_count": len(pre_kg.get("relations", [])),
            }
            return context
        # Determine route decided earlier
        route_info = context.results.get("route_document", {})
        route = route_info.get("route") or ("document" if document.should_use_document_level_kg() else "chunk")
        chunk_summary = context.results.get("chunk_content", {})
        chunk_count = chunk_summary.get("chunk_count")
        logger.info(
            "%s: extracting KG via route='%s' chunks=%s",
            document.id,
            route,
            chunk_count if chunk_count is not None else "?",
        )

        document = extract_knowledge_graph_for_document(
            document,
            context.services.kg_service,
            strategy=route,
            chunk_count=chunk_count,
        )
        context.set_document(document)

        kg = getattr(document, "knowledge_graph", {}) or {}
        entities = kg.get("entities", set())
        relations = kg.get("relations", [])
        strategy = "document-level" if route == "document" else ("chunk-level" if route == "chunk" else "skip")
        context.results[self.name] = {
            "entity_count": len(entities) if isinstance(entities, (set, list, tuple)) else 0,
            "relation_count": len(relations) if isinstance(relations, (list, tuple, set)) else 0,
            "strategy": strategy,
            "chunks_used": chunk_count or 0,
        }
        return context
