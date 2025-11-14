"""Step that persists the processed document to the configured storage backend."""

from __future__ import annotations

from knowledge_graph.persistence.sqlite.sql_lite import SqlLite
from knowledge_graph.settings.settings import get_settings
from ...document_pipeline import DocumentPipelineContext, PipelineStep

class PersistDocumentStep(PipelineStep):
    """Write the final document record to the database."""

    name = "persist_document"

    def __init__(self,enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        if not self.should_run(context):
            return context

        document = context.ensure_document()
        try:
            sqlite = SqlLite(settings=get_settings())  # uses default repo path resolution
            doc_repo = sqlite.document_repository()
            doc_repo.save_document(document)
            context.results[self.name] = {"persisted": True}
        except Exception as exc:  # pragma: no cover - defensive guard
            context.results[self.name] = {"persisted": False, "error": str(exc)}
            raise
        return context
