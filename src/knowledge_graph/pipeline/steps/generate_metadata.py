"""Step responsible for creating document-level metadata using the LLM service."""

from __future__ import annotations

import logging
import re
from typing import Any, List

from ..document_pipeline import DocumentPipelineContext, PipelineStep


logger = logging.getLogger("knowledgeAgent.pipeline.metadata")


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


def generate_document_metadata(document, llm_service):
    if not llm_service:
        logger.warning("LLM service not available; skipping document-level metadata generation")
        return document

    content = document.raw_content or ""
    raw_topics = llm_service.extract_topics(content)
    raw_keywords = llm_service.extract_keywords(content)

    cleaned_topics = _clean_list_from_response(raw_topics, "topics")
    cleaned_keywords = _clean_list_from_response(raw_keywords, "keywords")

    existing_tags = getattr(document.metadata, "tags", [])
    existing_categories = getattr(document.metadata, "categories", [])

    document.metadata.tags = list({*existing_tags, *cleaned_topics[:5]})
    document.metadata.categories = list({*existing_categories, *cleaned_keywords[:5]})
    document.metadata.word_count = len(content.split())

    if document.file_type.lower() in (".md", ".markdown"):
        headers = re.findall(r"^#{1,6}\s+(.+)$", content, re.MULTILINE)
        document.metadata.section_headers = headers

    document.is_metadata_generated = True
    logger.debug("Generated document-level metadata for %s", document.id)
    return document


class GenerateMetadataStep(PipelineStep):
    """Populate document-level metadata such as tags and categories."""

    name = "generate_metadata"

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        document = context.ensure_document()
        document = generate_document_metadata(document, context.services.llm_service)
        context.set_document(document)
        context.results[self.name] = {
            "tag_count": len(getattr(document.metadata, "tags", []) or []),
            "category_count": len(getattr(document.metadata, "categories", []) or []),
        }
        return context
