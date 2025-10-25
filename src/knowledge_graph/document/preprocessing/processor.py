from .parser import _get_parser_for_type
from ..manager.document_manager import DocumentManager
from ...core.db.sql_lite.service import SQLLiteService
import logging

class DocumentProcessor:
    """Orchestrates the document processing pipeline, to save raw files to postgres db ready to load into vector db."""
    def __init__(self, db_client, llm_service, llm_provider="openai"):
        self.document_manager = DocumentManager(
            llm_service=llm_service,
            db_client=db_client,
            llm_provider=llm_provider
        )
        self.logger = logging.getLogger("knowledgeAgent.document")
        self.db_client = db_client
        # Get database path from cache config

    def process_document(self, document_path, document_id, domain=None, tags=None):
        # Process new document
        self.logger.info(f"Processing new document: {document_path}")
        
        # Initialize document
        document = self._initialise_document(document_path, document_id, domain=domain, tags=tags)
        if document is None:
            self.logger.error("Failed to initialize document")
            return None
            
        # Process document through pipeline
        try:
            document = self._create_chunks(document)
            if document is None:
                self.logger.error("Failed to create chunks")
                return None
                
            document = self._create_metadata(document)
            if document is None:
                self.logger.error("Failed to create metadata")
                return None
            
            # Extract knowledge graph while document has all metadata
            document = self._extract_knowledge_graph(document)
            if document is None:
                self.logger.error("Failed to extract knowledge graph")
                return None
                
            self._save_document(document)
            return document

        except Exception as e:
            self.logger.error(f"Error processing document: {e}")
            return None

    def _initialise_document(self, document_path, document_id, domain=None, tags=None):
        """Initialise the document object."""
        try:
            document = self.document_manager.make_new_document(document_path, document_id)
            if document is None:
                self.logger.error("Document manager returned None")
                return None

            # Clean document content after loading
            document = self.document_manager.clean_document(document)
            
            # Add domain and tags to document metadata
            if domain or tags:
                if not hasattr(document, 'metadata') or document.metadata is None:
                    from .models.metadata import DocumentMetadata
                    document.metadata = DocumentMetadata()
                
                # Add domain as a category
                if domain:
                    if domain not in document.metadata.categories:
                        document.metadata.categories.append(domain)
                
                # Add tags
                if tags:
                    for tag in tags:
                        if tag not in document.metadata.tags:
                            document.metadata.tags.append(tag)

            self.logger.info(f"Document initialized with ID: {document.id}")
            return document
        except Exception as e:
            self.logger.error(f"Error initializing document: {e}")
            return None
    
    def _create_chunks(self, document):
        document = self.document_manager.chunk_document(document)
        document = self.document_manager.enrich_document_chunks(document)
        return document
    
    def _create_metadata(self, document):
        document = self.document_manager.generate_document_level_metadata(document)
        return document

    def _extract_knowledge_graph(self, document):
        """Extract knowledge graph from document"""
        try:
            # Use the document manager's KG extraction method
            document = self.document_manager.extract_knowledge_graph(document)
            self.logger.info(f"Knowledge graph extracted for document {document.id}")
            return document
        except Exception as e:
            self.logger.error(f"Error extracting knowledge graph: {e}")
            return document
    
    def _save_document(self, document):
        """Save document to SQLite"""
        try:
            if not self.db_client:
                self.logger.warning("Database not initialized, skipping save")
                return document
            self.db_client.save_document(document)            
            self.logger.info(f"Document saved to database")
        except Exception as e:
            self.logger.error(f"Error saving to database: {e}")
        return document

    

