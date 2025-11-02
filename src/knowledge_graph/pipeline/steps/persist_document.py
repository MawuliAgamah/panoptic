"""Step that persists the processed document to the configured storage backend."""

from __future__ import annotations

from ..document_pipeline import DocumentPipelineContext, PipelineStep

class PersistDocumentStep(PipelineStep):
    """Write the final document record to the database."""

    name = "persist_document"

    def __init__(self, db_client, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled and db_client is not None)
        self.db_client = db_client

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        if not self.should_run(context):
            return context

        document = context.ensure_document()
        try:
            self.db_client.save_document(document)
            context.results[self.name] = {"persisted": True}
        except Exception as exc:  # pragma: no cover - defensive guard
            context.results[self.name] = {"persisted": False, "error": str(exc)}
            raise
        return context
