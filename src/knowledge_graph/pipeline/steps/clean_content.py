"""Step that normalises raw content into clean text suitable for downstream steps."""

from __future__ import annotations

import logging
import re
from typing import List, Match

from ..document_pipeline import DocumentPipelineContext, PipelineStep


logger = logging.getLogger("knowledgeAgent.pipeline.clean")


def clean_document_content(document):
    """Clean markdown/Obsidian syntax and populate clean_content."""
    if not document.raw_content:
        document.clean_content = ""
        document.wiki_links = []
        document.is_preprocessed = True
        return document

    content = document.raw_content

    # Remove embedded files first (they start with !)
    content = re.sub(r"!\[\[(.*?)\]\]", "", content)

    # Extract wiki links after removing embeds
    wiki_links = re.findall(r"\[\[(.*?)\]\]", content)
    document.wiki_links = wiki_links

    # Remove Obsidian-specific syntax
    content = re.sub(r"\[\[(.*?)\]\]", r"\1", content)
    content = re.sub(r"%%.*?%%", "", content, flags=re.DOTALL)

    # Strip markdown emphasis/code syntax
    content = re.sub(r"\*\*(.*?)\*\*", r"\1", content)
    content = re.sub(r"\*(.*?)\*", r"\1", content)
    content = re.sub(r"`([^`]+)`", r"\1", content)
    content = re.sub(r"#{1,6}\s+", "", content)

    code_blocks: List[str] = []

    def preserve_code_block(match: Match[str]) -> str:
        code_blocks.append(match.group(0))
        return f"__CODE_BLOCK_{len(code_blocks) - 1}__"

    content = re.sub(r"```.*?```", preserve_code_block, content, flags=re.DOTALL)
    content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)

    for idx, code_block in enumerate(code_blocks):
        content = content.replace(f"__CODE_BLOCK_{idx}__", code_block)

    document.clean_content = content.strip()
    document.is_preprocessed = True
    raw_len = len(document.raw_content or "")
    clean_len = len(document.clean_content or "")
    raw_nl = (document.raw_content or "").count("\n")
    clean_nl = (document.clean_content or "").count("\n")
    logger.info(
        "Cleaned document %s: raw_chars=%d clean_chars=%d raw_nl=%d clean_nl=%d wiki_links=%d",
        document.id,
        raw_len,
        clean_len,
        raw_nl,
        clean_nl,
        len(wiki_links),
    )
    return document


class CleanContentStep(PipelineStep):
    """Normalize document text for subsequent pipeline steps."""

    name = "clean_content"

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        document = context.ensure_document()
        document = clean_document_content(document)
        context.set_document(document)
        context.results[self.name] = {
            "raw_length": len(document.raw_content or ""),
            "clean_length": len(document.clean_content or ""),
            "wiki_links": len(getattr(document, "wiki_links", []) or []),
            "raw_newlines": (document.raw_content or "").count("\n"),
            "clean_newlines": (document.clean_content or "").count("\n"),
        }
        return context
