from typing import Optional
import logging
import uuid
from ..pipeline import DocumentPipeline, DocumentPipelineConfig, DocumentPipelineServices
from ..pipeline.steps import (
    LoadDocumentStep,
    CleanContentStep,
    ChunkContentStep,
    ExtractKnowledgeGraphStep,
    PersistDocumentStep,
    RouteDocumentStep,
)
from ..knowledge_graph.service import KnowledgeGraphService

class DocumentService:
    """Service for document operations, used by the client"""

    def __init__(
        self,
        db_client,
        llm_service=None,
        llm_provider="openai",
        pipeline_config: Optional[DocumentPipelineConfig] = None,
        kg_service=None,
    ):
        self.logger = logging.getLogger("knowledgeAgent.document")
        self.db_client = db_client
        self.llm_service = llm_service
        self.llm_provider = llm_provider

        if kg_service is not None:
            self.kg_service = kg_service
        elif db_client is not None:
            self.kg_service = KnowledgeGraphService(
                db_client=db_client,
                llm_service=llm_service,
                llm_provider=llm_provider,
            )
        else:
            self.kg_service = None

        self.pipeline_config = pipeline_config or DocumentPipelineConfig()
        self.pipeline = self._create_pipeline(self.pipeline_config)

    def _create_pipeline(self, config: DocumentPipelineConfig) -> DocumentPipeline:
        enrichment_enabled = config.enable_enrichment
        kg_enabled = config.enable_kg_extraction
        persistence_enabled = config.enable_persistence and self.db_client is not None

        steps = [
            LoadDocumentStep(),
            CleanContentStep(),
            RouteDocumentStep(),
            ChunkContentStep(
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                chunker_type=config.chunker_type,
            ),
            ExtractKnowledgeGraphStep(
                enabled=kg_enabled,
                chunk_size=config.chunk_size,
                chunk_overlap=config.chunk_overlap,
                chunker_type=config.chunker_type,
            ),
            PersistDocumentStep(self.db_client, enabled=persistence_enabled),
        ]

        services = DocumentPipelineServices(
            llm_service=self.llm_service,
            kg_service=self.kg_service,
            db_client=self.db_client,
            llm_provider=self.llm_provider,
        )

        return DocumentPipeline(
            services=services,
            config=config,
            steps=steps,
        )

    def build_pipeline(self, config: DocumentPipelineConfig) -> DocumentPipeline:
        """Construct a new pipeline instance using the provided configuration."""
        return self._create_pipeline(config)

    def process_document(self, document_path, document_id, domain=None, tags=None, pipeline=None):
        """Run the configured pipeline and return the processed document."""
        active_pipeline = pipeline or self.pipeline
        return active_pipeline.run(
            document_path=document_path,
            document_id=document_id,
            domain=domain,
            tags=tags,
        )
        
    def add_document(self, document_path, document_type=None, document_id=None, domain=None, tags=None, cache=True):
        """Add a document to the system"""
        try:
            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())

            document = self.process_document(document_path, document_id, domain=domain, tags=tags)
            if document is None:
                self.logger.error("Failed to process document")
                return None
            return document.id
            
        except Exception as e:
            self.logger.error(f"Error adding document: {e}")
            return None
        
    def delete_document(self,document_id: str):
        self.db_client.delete_document(document_id)
        self.logger.info(f"Document deleted with ID: {document_id}")
        

    
    
