from .models.document import Document, DocumentMetadata
from .models.chunk import TextChunk
from .preprocessing.processor import DocumentProcessor
#from .cache.cache_manager import CacheManager
from typing import Dict, Any
import logging
import uuid

class DocumentService:
    """Service for document operations, used by the client"""

    def __init__(self, db_client, llm_service=None):
        self.logger = logging.getLogger("knowledgeAgent.document")
        self.db_client = db_client
        self.llm_service = llm_service
        
        # initialize document processor
        self.processor = DocumentProcessor(db_client=self.db_client,  llm_service=self.llm_service)
        
    def add_document(self, document_path, document_type=None, document_id=None, cache=True):
        """Add a document to the system"""
        try:
            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())
                
            # Process document
            document = self.processor.process_document(document_path, document_id)
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
        

    
    