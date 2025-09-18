from src.knowledgeAgent.document.models.document import Document
from src.knowledgeAgent.document.models.metadata import DocumentMetadata
from src.knowledgeAgent.document.models.chunk import TextChunk, ChunkMetadata
from datetime import datetime
import json

class DatabaseClient:
    """Client for database operations"""
    
    def __init__(self, db_config):
        self.db_service = None
        self.db_config = db_config
        self._configure_database(db_config)
        
    def _configure_database(self, db_config):
        """Configure the database based on type"""
        db_type = db_config.get('db_type')
        
        if db_type == 'sqlite':
            from src.knowledgeAgent.core.db.sql_lite.service import SQLLiteService
            self.db_service = SQLLiteService(db_path=db_config.get('db_location'))
        # keep comments for future reference
        # elif db_type == 'postgres':
            # from src.knowledgeAgent.core.db.postgres import PostgresDB
            # self.db_service = PostgresDB(
            #     host=db_config.get('host'),
            #     port=db_config.get('port'),
            #     database=db_config.get('database'),
            #     user=db_config.get('username'),
            #     password=db_config.get('password')
            # )
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
        
    
    def save_document(self, document):
        """Save document"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        return self.db_service.save_document(document)
    
    def delete_document(self, document_id):
        """Delete document"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        return self.db_service.delete_document(document_id)
    
    def get_chunks(self, document_id):
        """Get document chunks"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        return self.db_service.get_chunks(document_id)
    
    def get_document(self, document_id):
        """Get document by ID and return as Document model"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        
        # Get document data from database
        doc_data = self.db_service.retrieve_document(document_id)
        if not doc_data:
            return None
        
        # Extract document and chunks from response
        document_data = doc_data.get('document', [])
        if not document_data or len(document_data) == 0:
            return None
            
        # First row contains document data 
        document_row = document_data[0]
        document_dict = {
            'document_id': document_row[0],
            'file_path': document_row[1],
            'hash': document_row[2],
            'document_type': document_row[3],
            'title': document_row[4],
            'summary': document_row[5],
            'raw_content': document_row[6],
            'clean_content': document_row[7],
            'created_at': document_row[8],
            'updated_at': document_row[9],
            'last_modified': document_row[10]
        }
        
        # Get chunks data
        chunks_data = doc_data.get('chunks', [])
        text_chunks = []
        
        # Ensure chunks_data is a list
        if chunks_data and isinstance(chunks_data, list):
            for chunk_row in chunks_data:
                # Convert row to dict
                chunk_dict = {
                    'id': chunk_row[0],
                    'document_id': chunk_row[1],
                    'content': chunk_row[2],
                    'chunk_index': chunk_row[3],
                    'word_count': chunk_row[4],
                    'token_count': chunk_row[5],
                    'language': chunk_row[6],
                    'topics': chunk_row[7],
                    'keywords': chunk_row[8],
                    'start_index': chunk_row[9],
                    'end_index': chunk_row[10],
                    'previous_chunk_id': chunk_row[11],
                    'next_chunk_id': chunk_row[12]
                }
                
                # Parse topics and keywords from JSON strings if needed
                topics = []
                keywords = []
                topics_str = chunk_dict.get('topics')
                if topics_str:
                    try:
                        topics = json.loads(topics_str)
                    except:
                        topics = topics_str.split(',') if topics_str else []
                        
                keywords_str = chunk_dict.get('keywords')
                if keywords_str:
                    try:
                        keywords = json.loads(keywords_str)
                    except:
                        keywords = keywords_str.split(',') if keywords_str else []
                
                # Create chunk metadata
                chunk_metadata = ChunkMetadata(
                    start_index=chunk_dict.get('start_index', 0),
                    end_index=chunk_dict.get('end_index', 0),
                    word_count=chunk_dict.get('word_count', 0),
                    language=chunk_dict.get('language', 'en'),
                    topics=topics,
                    keywords=keywords
                )
                
                # Create text chunk
                text_chunk = TextChunk(
                    id=str(chunk_dict.get('id')),
                    document_id=document_id,
                    content=chunk_dict.get('content', ''),
                    metadata=chunk_metadata,
                    previous_chunk_id=str(chunk_dict.get('previous_chunk_id')) if chunk_dict.get('previous_chunk_id') else None,
                    next_chunk_id=str(chunk_dict.get('next_chunk_id')) if chunk_dict.get('next_chunk_id') else None
                )
                text_chunks.append(text_chunk)
        
        # Create metadata object - using only document_data now
        metadata = DocumentMetadata(
            document_id=document_id,
            metadata_id=document_id,  # Use document_id as metadata_id
            title=document_dict.get('title'),
            created_date=document_dict.get('created_at'),
            modified_date=document_dict.get('updated_at')
        )
        
        # Create document object
        document = Document(
            id=document_id,
            filename=document_dict.get('file_path', '').split('/')[-1],
            file_path=document_dict.get('file_path', ''),
            file_type=document_dict.get('document_type', ''),
            file_size=0,  # Not available from database
            title=document_dict.get('title', ''),
            raw_content=document_dict.get('raw_content', ''),  # Use stored raw content
            clean_content=document_dict.get('clean_content', ''),  # Use stored clean content
            metadata=metadata,
            textChunks=text_chunks,
            document_created_at=document_dict.get('created_at', datetime.now()),
            preprocessed_at=document_dict.get('updated_at'),
            is_cached=True,
            cache_created_at=document_dict.get('created_at'),
            cache_updated_at=document_dict.get('updated_at')
        )
        
        return document

    def save_entities_and_relationships(self, document_id, chunk_id, ontology):
        """Save entities and relationships extracted from ontology"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        return self.db_service.save_entities_and_relationships(document_id, chunk_id, ontology)
    
    def get_document_ontology(self, document_id):
        """Get all entities and relationships for a document"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        return self.db_service.get_document_ontology(document_id)
    
    def get_chunk_ontology(self, chunk_id):
        """Get all entities and relationships for a chunk"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        return self.db_service.get_chunk_ontology(chunk_id)
    
    def save_document_ontology(self, document_id, ontology):
        """Save full document ontology"""
        if not self.db_service:
            raise ValueError("Database service not initialized")
        return self.db_service.save_document_ontology(document_id, ontology)


        
        