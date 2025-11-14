from __future__ import annotations

from knowledge_graph.persistence.sqlite.sql_lite import SqlLite
from ...document_pipeline import DocumentPipelineContext, PipelineStep


class PersistDocumentStep(PipelineStep):
    def __init__(self, enabled: bool = True):
        super().__init__(enabled=enabled)


    def should_run(self, context: DocumentPipelineContext):
        return self.enabled and context.document is not None

    def run(self, context: DocumentPipelineContext):
        if not self.should_run(context):
            return context
        else:
            sqlite = SqlLite()  # uses default repo path resolution
            doc_repo = sqlite.tabular_document_repository()
            doc_repo.save_csv_profile(context.csv_profile)
        return context
