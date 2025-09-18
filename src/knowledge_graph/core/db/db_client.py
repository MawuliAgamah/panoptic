from knowledge_graph.document.models.document import Document
from knowledge_graph.document.models.metadata import DocumentMetadata
from knowledge_graph.document.models.chunk import TextChunk, ChunkMetadata
from knowledge_graph.core.db.neo4j.service import Neo4jService
from datetime import datetime
import json
import logging

logger = logging.getLogger(__name__)

class DatabaseClient:
    """Dual database client for SQLite (documents/chunks) and Neo4j (knowledge graphs)"""

    def __init__(self, db_config):
        self.sqlite_service = None
        self.neo4j_service = None
        self.db_config = db_config
        self._configure_databases(db_config)

    def _configure_databases(self, db_config):
        """Configure both SQLite and Neo4j databases"""

        # Configure SQLite for documents and chunks
        sqlite_config = db_config.get('sqlite', {})
        if sqlite_config:
            from knowledge_graph.core.db.sql_lite.service import SQLLiteService
            self.sqlite_service = SQLLiteService(db_path=sqlite_config.get('db_location'))
            logger.info("SQLite service configured")

        # Configure Neo4j for knowledge graphs
        neo4j_config = db_config.get('neo4j', {})
        if neo4j_config:
            try:
                self.neo4j_service = Neo4jService(neo4j_config)
                logger.info("Neo4j service configured")
            except Exception as e:
                logger.warning(f"Neo4j service configuration failed: {e}. Knowledge graph features will be unavailable.")
                self.neo4j_service = None

        if not self.sqlite_service and not self.neo4j_service:
            raise ValueError("At least one database service must be configured")
        
    
    # Document operations (SQLite)
    def save_document(self, document):
        """Save document to SQLite"""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")
        return self.sqlite_service.save_document(document)

    def delete_document(self, document_id):
        """Delete document from SQLite and Neo4j"""
        results = {}

        if self.sqlite_service:
            results['sqlite'] = self.sqlite_service.delete_document(document_id)

        if self.neo4j_service:
            results['neo4j'] = self.neo4j_service.delete_document_graph(document_id)

        return results

    def get_chunks(self, document_id):
        """Get document chunks from SQLite"""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")
        return self.sqlite_service.get_chunks(document_id)

    def get_document(self, document_id):
        """Get document by ID and return as Document model"""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")

        # Get document data from SQLite
        doc_data = self.sqlite_service.retrieve_document(document_id)
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

    # Knowledge graph operations (Neo4j)
    def save_knowledge_graph(self, document_id, kg_graph):
        """Save knowledge graph to Neo4j"""
        if not self.neo4j_service:
            logger.warning(f"Neo4j service not available. Cannot save knowledge graph for document {document_id}")
            return False
        return self.neo4j_service.save_knowledge_graph(document_id, kg_graph)

    def get_document_entities(self, document_id):
        """Get all entities for a document from Neo4j"""
        if not self.neo4j_service:
            logger.warning("Neo4j service not available")
            return []
        return self.neo4j_service.get_document_entities(document_id)

    def get_document_relationships(self, document_id):
        """Get all relationships for a document from Neo4j"""
        if not self.neo4j_service:
            logger.warning("Neo4j service not available")
            return []
        return self.neo4j_service.get_document_relationships(document_id)

    def search_entities(self, search_term, limit=10):
        """Search entities across knowledge graph"""
        if not self.neo4j_service:
            logger.warning("Neo4j service not available")
            return []
        return self.neo4j_service.search_entities(search_term, limit)

    def get_entity_connections(self, entity_name, depth=1):
        """Get connections for an entity"""
        if not self.neo4j_service:
            logger.warning("Neo4j service not available")
            return []
        return self.neo4j_service.get_entity_connections(entity_name, depth)

    def get_graph_statistics(self):
        """Get knowledge graph statistics"""
        if not self.neo4j_service:
            logger.warning("Neo4j service not available")
            return {"entities": 0, "documents": 0, "relationships": 0}
        return self.neo4j_service.get_graph_statistics()

    def delete_document_knowledge_graph(self, document_id):
        """Delete knowledge graph data for a document"""
        if not self.neo4j_service:
            logger.warning("Neo4j service not available")
            return False
        return self.neo4j_service.delete_document_graph(document_id)

    def test_connections(self):
        """Test both database connections"""
        results = {}

        if self.sqlite_service:
            try:
                # Test SQLite by attempting a simple query
                results['sqlite'] = True
            except Exception as e:
                logger.error(f"SQLite connection test failed: {e}")
                results['sqlite'] = False

        if self.neo4j_service:
            results['neo4j'] = self.neo4j_service.test_connection()
        else:
            results['neo4j'] = False

        return results

    # Legacy ontology methods (for backward compatibility - delegate to SQLite)
    def save_entities_and_relationships(self, document_id, chunk_id, ontology):
        """Save entities and relationships (legacy method - uses SQLite)"""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")
        return self.sqlite_service.save_entities_and_relationships(document_id, chunk_id, ontology)

    def get_document_ontology(self, document_id):
        """Get document ontology (legacy method - uses SQLite)"""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")
        return self.sqlite_service.get_document_ontology(document_id)

    def get_chunk_ontology(self, chunk_id):
        """Get chunk ontology (legacy method - uses SQLite)"""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")
        return self.sqlite_service.get_chunk_ontology(chunk_id)

    def save_document_ontology(self, document_id, ontology):
        """Save document ontology (legacy method - uses SQLite)"""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")
        return self.sqlite_service.save_document_ontology(document_id, ontology)

    def close(self):
        """Close all database connections"""
        if self.sqlite_service and hasattr(self.sqlite_service, 'close'):
            self.sqlite_service.close()

        if self.neo4j_service:
            self.neo4j_service.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


        
        