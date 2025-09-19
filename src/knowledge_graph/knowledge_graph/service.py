from knowledge_graph.llm.kg_extractor.service import KGExtractionService
from typing import Dict, Any, List, Optional
import logging

logger = logging.getLogger(__name__)

class KnowledgeGraphService:
    """
    Pure knowledge graph operations service.

    This service handles all KG extraction and management operations,
    wrapping the KGExtractionService and providing higher-level KG operations.
    """

    def __init__(self, db_client, llm_service, llm_provider: str = "openai"):
        self.db_client = db_client
        self.llm_service = llm_service

        # Initialize the KG extraction service with kggen integration
        llm_config = {}
        if hasattr(llm_service, 'config'):
            llm_config = llm_service.config

        self.kg_extractor = KGExtractionService(
            llm_provider=llm_provider,
            **llm_config
        )

        logger.info(f"KnowledgeGraphService initialized with {llm_provider} provider")

    def extract_from_document(self, document) -> Dict[str, Any]:
        """
        Extract knowledge graph from a document object.

        Args:
            document: Document object to extract from

        Returns:
            Dictionary with entities, relations, and metadata
        """
        logger.info(f"Extracting knowledge graph from document: {document.id}")

        result = self.kg_extractor.extract_from_document(document)

        # Save to database
        if result and (result.get('entities') or result.get('relations')):
            try:
                # Prepare document metadata for entities
                document_metadata = {
                    'title': document.title,
                    'file_path': document.file_path,
                    'file_type': document.file_type,
                    'file_size': getattr(document, 'file_size', 0),
                    'word_count': len(document.clean_content.split()) if document.clean_content else 0,
                    'processing_strategy': 'Document-level' if document.should_use_document_level_kg() else 'Chunk-level',
                    'token_estimate': len(document.clean_content.split()) * 1.3 if document.clean_content else 0,
                    'tags': getattr(document.metadata, 'tags', []) if hasattr(document, 'metadata') and document.metadata else [],
                    'categories': []
                }

                self.db_client.save_knowledge_graph(document.id, result, document_metadata)
                logger.info(f"Saved knowledge graph for document {document.id}")
            except Exception as e:
                logger.warning(f"Failed to save knowledge graph to database: {e}")

        return result

    def extract_from_chunks(self, chunks: List[str], document_id: str) -> Dict[str, Any]:
        """
        Extract knowledge graph from text chunks and merge results.

        Args:
            chunks: List of text chunks
            document_id: Document ID for context

        Returns:
            Merged knowledge graph results
        """
        logger.info(f"Extracting knowledge graph from {len(chunks)} chunks for document: {document_id}")

        result = self.kg_extractor.extract_from_chunks(chunks, document_id)

        # Save to database
        if result and (result.get('entities') or result.get('relations')):
            try:
                # Get document metadata for chunks-based extraction
                document = self.db_client.get_document(document_id)
                document_metadata = {}
                if document:
                    document_metadata = {
                        'title': document.title,
                        'file_path': document.file_path,
                        'file_type': document.file_type,
                        'file_size': getattr(document, 'file_size', 0),
                        'word_count': len(document.clean_content.split()) if document.clean_content else 0,
                        'processing_strategy': 'Chunk-level',
                        'token_estimate': len(document.clean_content.split()) * 1.3 if document.clean_content else 0,
                        'tags': getattr(document.metadata, 'tags', []) if hasattr(document, 'metadata') and document.metadata else [],
                        'categories': []
                    }

                self.db_client.save_knowledge_graph(document_id, result, document_metadata)
                logger.info(f"Saved knowledge graph for document {document_id}")
            except Exception as e:
                logger.warning(f"Failed to save knowledge graph to database: {e}")

        return result

    def extract_from_text(
        self,
        text: str,
        context: Optional[str] = None,
        strategy: str = "detailed",
        track_metadata: bool = True
    ) -> Dict[str, Any]:
        """
        Extract knowledge graph directly from text.

        Args:
            text: Input text to extract from
            context: Optional context for better extraction
            strategy: Extraction strategy ("simple", "detailed")
            track_metadata: Whether to track extraction metadata

        Returns:
            Dictionary with entities, relations, and optionally metadata
        """
        return self.kg_extractor.extract_from_text(
            text=text,
            context=context,
            strategy=strategy,
            track_metadata=track_metadata
        )

    def get_document_knowledge_graph(self, document_id: str) -> Dict[str, Any]:
        """
        Get knowledge graph data for a document.

        Args:
            document_id: Document identifier

        Returns:
            Dictionary with entities and relationships
        """
        try:
            return self.db_client.get_document_ontology(document_id)
        except Exception as e:
            logger.error(f"Error retrieving knowledge graph for document {document_id}: {e}")
            return {'entities': [], 'relationships': []}

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any]) -> bool:
        """
        Save knowledge graph data for a document.

        Args:
            document_id: Document identifier
            kg_data: Knowledge graph data with entities and relations

        Returns:
            True if successful
        """
        try:
            return self.db_client.save_knowledge_graph(document_id, kg_data)
        except Exception as e:
            logger.error(f"Error saving knowledge graph for document {document_id}: {e}")
            return False

    def delete_document_knowledge_graph(self, document_id: str) -> bool:
        """
        Delete knowledge graph data for a document.

        Args:
            document_id: Document identifier

        Returns:
            True if successful
        """
        try:
            return self.db_client.delete_document_knowledge_graph(document_id)
        except Exception as e:
            logger.error(f"Error deleting knowledge graph for document {document_id}: {e}")
            return False

    # Legacy method for backward compatibility
    def agentic_ontology_extraction(self, document_id: str) -> Dict[str, Any]:
        """
        Legacy method for agentic ontology extraction.
        Now delegates to the modern KG extraction pipeline.

        Args:
            document_id: Document identifier

        Returns:
            Extraction results
        """
        logger.info(f"Using legacy agentic_ontology_extraction for document: {document_id}")

        document = self.db_client.get_document(document_id)
        if not document:
            logger.error(f"Document {document_id} not found")
            return {'entities': set(), 'relations': []}

        # Use the modern extraction pipeline
        if document.should_use_document_level_kg():
            result = self.extract_from_document(document)
        else:
            # Ensure document is chunked
            if not document.textChunks:
                logger.warning("Document not chunked, cannot extract KG")
                return {'entities': set(), 'relations': []}

            chunk_texts = [chunk.content for chunk in document.textChunks if chunk.content.strip()]
            result = self.extract_from_chunks(chunk_texts, document_id)

        return result
