"""Step that enriches chunk metadata using the LLM service."""

from __future__ import annotations

import logging
from typing import Any, List

from ..document_pipeline import DocumentPipelineContext, PipelineStep


logger = logging.getLogger("knowledgeAgent.pipeline.enrich")


def _clean_list_from_response(response: Any, key: str) -> List[str]:
    if not response:
        return []
    if isinstance(response, dict) and key in response:
        items = response[key]
    elif isinstance(response, list):
        items = response
    else:
        return []

    cleaned: List[str] = []
    for item in items:
        if isinstance(item, str):
            value = item.replace("#", "").strip()
            if value:
                cleaned.append(value)
    return cleaned


def enrich_chunks_with_llm(document, llm_service):
    if not llm_service:
        logger.warning("LLM service not available; skipping enrichment")
        return document

    if not document.textChunks:
        logger.warning("Document %s has no chunks to enrich", document.id)
        return document

    for chunk in document.textChunks:
        raw_topics = llm_service.extract_topics(chunk.content)
        raw_keywords = llm_service.extract_keywords(chunk.content)

        chunk.metadata.topics = _clean_list_from_response(raw_topics, "topics")
        chunk.metadata.keywords = _clean_list_from_response(raw_keywords, "keywords")

    logger.debug("Enriched %d chunks for document %s", len(document.textChunks), document.id)
    return document


class EnrichChunksStep(PipelineStep):
    """Optional enrichment step that augments chunk metadata."""

    name = "enrich_chunks"

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        if not self.should_run(context):
            return context

        document = context.ensure_document()
        document = enrich_chunks_with_llm(document, context.services.llm_service)
        context.set_document(document)
        context.results[self.name] = {
            "chunk_count": len(document.textChunks or []),
        }
        return context
