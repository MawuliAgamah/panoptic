"""Step that determines the optimal processing route for a document.

Sets a routing decision in the pipeline context to guide downstream steps:
 - 'skip'     -> Do not extract a knowledge graph
 - 'document' -> Run document-level KG extraction (no chunking)
 - 'chunk'    -> Run chunk-level KG extraction (requires chunking step)
"""

from __future__ import annotations

import logging
from ..document_pipeline import DocumentPipelineContext, PipelineStep


logger = logging.getLogger("knowledgeAgent.pipeline.route")


class RouteDocumentStep(PipelineStep):
    """Decide whether to skip, use document-level, or chunk-level processing."""

    name = "route_document"

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        document = context.ensure_document()

        # Default route is 'skip' unless content passes validation
        if not document.validate_content_for_kg():
            route = "skip"
        else:
            route = "document" if document.should_use_document_level_kg() else "chunk"

        # Prefer chunk route for PDFs to enable page-level chunking and provenance
        try:
            file_type = (getattr(document, "file_type", "") or "").lower()
            if file_type in {".pdf", "pdf"} and route != "skip":
                route = "chunk"
        except Exception:
            pass

        context.results[self.name] = {
            "route": route,
            "file_type": getattr(document, "file_type", ""),
            "token_estimate": document.estimate_token_count(),
        }
        logger.info("Routing decision for %s: %s", document.id, route)
        return context
