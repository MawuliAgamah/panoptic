"""Step that coordinates knowledge graph extraction."""

from __future__ import annotations

import logging
from datetime import datetime

from typing import Optional

from ..document_pipeline import DocumentPipelineContext, PipelineStep
from .clean_content import clean_document_content
from .chunk_content import chunk_document


logger = logging.getLogger("knowledgeAgent.pipeline.kg")


def extract_knowledge_graph_for_document(
    document,
    kg_service,
    *,
    chunk_size: int,
    chunk_overlap: int,
    chunker_type: str,
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

    use_document_level = document.should_use_document_level_kg()
    if use_document_level:
        result = kg_service.extract_from_document(document)
    else:
        if not document.textChunks:
            chunk_document(
                document,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                chunker_type=chunker_type,
            )

        chunk_texts = [chunk.content for chunk in document.textChunks if chunk.content.strip()]
        if chunk_texts:
            result = kg_service.extract_from_chunks(chunk_texts, document.id)
            document.knowledge_graph = result
            document.is_kg_extracted = True
            document.kg_extracted_at = datetime.now()
            document.kg_extraction_metadata = {
                "strategy_used": "chunk-level",
                "chunk_count": len(chunk_texts),
                "entity_count": len(result.get("entities", set())),
                "relation_count": len(result.get("relations", [])),
            }
        else:
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
        chunk_summary = context.results.get("chunk_content", {})
        chunk_count = chunk_summary.get("chunk_count")
        document = extract_knowledge_graph_for_document(
            document,
            context.services.kg_service,
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            chunker_type=self.chunker_type,
            chunk_count=chunk_count,
        )
        context.set_document(document)

        kg = getattr(document, "knowledge_graph", {}) or {}
        entities = kg.get("entities", set())
        relations = kg.get("relations", [])
        strategy = (
            "document-level"
            if document.should_use_document_level_kg()
            else "chunk-level"
        )
        context.results[self.name] = {
            "entity_count": len(entities) if isinstance(entities, (set, list, tuple)) else 0,
            "relation_count": len(relations) if isinstance(relations, (list, tuple, set)) else 0,
            "strategy": strategy,
            "chunks_used": chunk_count or 0,
        }
        return context
