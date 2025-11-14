"""Pipeline factory that builds orchestrators based on file type."""

from __future__ import annotations

from typing import Optional

from .document_pipeline import DocumentPipeline # , DocumentPipelineConfig, DocumentPipelineServices
from .pdf.steps import (
    LoadDocumentStep,
    CleanContentStep,
    RouteDocumentStep,
    ChunkContentStep,
    ExtractKnowledgeGraphStep,
    PersistDocumentStep,
)

from .tabular.steps import (
    LoadCSVStep,
    GenerateCsvProfileStep,
    AnalyseCsvWithAgentStep,
    GenerateOntologyWithAgentStep,
    GenerateMappingFromOntologyStep,
    BindAttributesFromOntologyStep,
    PopulateMissingPrimaryKeysStep,
    TransformAndPersistKGStep,
)


class PipelineFactory:
    """Create modality-specific pipelines for a given file path or type."""

    @staticmethod
    def for_file(
        file_path: str,
        # services: DocumentPipelineServices,
        *,
        config: Optional[DocumentPipelineConfig] = None,
    ) -> DocumentPipeline:
        file_type = (file_path.split(".")[-1] if "." in file_path else "").lower()
        if file_type == "csv":
            return PipelineFactory.csv_pipeline()
        # Default/general pipeline
        return PipelineFactory.general_pipeline()

    @staticmethod
    def csv_pipeline(
        # services: DocumentPipelineServices,
        # *,
        # config: Optional[DocumentPipelineConfig] = None,
    ) -> DocumentPipeline:
        # cfg = config or DocumentPipelineConfig()
        steps = [
            LoadCSVStep(),
            GenerateCsvProfileStep(enabled=True, sample_rows=50),
            AnalyseCsvWithAgentStep(enabled=True, sample_rows=30),
            GenerateOntologyWithAgentStep(enabled=True),
            GenerateMappingFromOntologyStep(enabled=True),
            BindAttributesFromOntologyStep(enabled=True),
            PopulateMissingPrimaryKeysStep(enabled=True),
            TransformAndPersistKGStep(enabled=True),
        ]
        return DocumentPipeline(steps=steps)

    @staticmethod
    def general_pipeline(
        # services: DocumentPipelineServices,
        # *,
        # config: Optional[DocumentPipelineConfig] = None,
    ) -> DocumentPipeline:
        # cfg = config or DocumentPipelineConfig()
        steps = [
            LoadDocumentStep(),
            CleanContentStep(),
            RouteDocumentStep(),
            ChunkContentStep(
                chunk_size=cfg.chunk_size,
                chunk_overlap=cfg.chunk_overlap,
                chunker_type=cfg.chunker_type,
            ),
            ExtractKnowledgeGraphStep(
                enabled=cfg.enable_kg_extraction,
                chunk_size=cfg.chunk_size,
                chunk_overlap=cfg.chunk_overlap,
                chunker_type=cfg.chunker_type,
            ),
            PersistDocumentStep(enabled=True),
        ]
        return DocumentPipeline(steps=steps)
