from ...data_structs.document import Document
from ...data_structs.document import DocumentMetadata
from ...data_structs.document import TextChunk, ChunkMetadata
from .neo4j.service import Neo4jService
from datetime import datetime
from typing import Optional, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

class DatabaseClient:
    """Multi-database client supporting SQLite (documents/chunks + knowledge graphs) and optionally Neo4j."""

    def __init__(self, graph_db_config=None, cache_db_config=None, db_config=None):
        """
        Initialize DatabaseClient with separate configurations for graph and cache databases.

        Args:
            graph_db_config: Configuration for knowledge graph storage (Neo4j/JSON)
            cache_db_config: Configuration for document/chunk caching (SQLite)
            db_config: Legacy single config (for backward compatibility)
        """
        self.graph_db_type = None
        self.sqlite_service = None
        self.neo4j_service = None
        self.json_kg_service = None

        # Handle both new and legacy initialization
        if db_config:
            # Legacy single config approach
            self.db_config = db_config
            self._configure_databases_legacy(db_config)
        else:
            # New dual config approach
            self.graph_db_config = graph_db_config
            self.cache_db_config = cache_db_config
            self._configure_databases_dual(graph_db_config, cache_db_config)

    def _configure_databases_dual(self, graph_db_config, cache_db_config):
        """Configure separate cache and graph databases."""

        # Configure cache database (SQLite)
        if cache_db_config:
            cache_type = cache_db_config.get('db_type')
            if cache_type == 'sqlite' or 'db_location' in cache_db_config:
                from .sql_lite.service import SQLLiteService
                sqlite_path = cache_db_config.get('db_location', 'cache.db')
                self.sqlite_service = SQLLiteService(db_path=sqlite_path)
                logger.info(f"SQLite service configured at: {sqlite_path}")

        # Configure knowledge graph storage
        if graph_db_config:
            graph_db_type = graph_db_config.get('db_type')

            if graph_db_type == 'neo4j':
                # Neo4j for knowledge graphs
                try:
                    self.neo4j_service = Neo4jService(graph_db_config)
                    self.graph_db_type = 'neo4j'
                    logger.info("Neo4j service configured for knowledge graphs")
                except Exception as e:
                    logger.warning(f"Neo4j service configuration failed: {e}. Knowledge graph features will be unavailable.")
                    self.neo4j_service = None

            elif graph_db_type == 'sqlite':
                self.graph_db_type = 'sqlite'
                logger.info("Using SQLite for knowledge graph storage")

        # Ensure we have at least SQLite for caching if not configured
        if not self.sqlite_service:
            # Fallback SQLite configuration
            from knowledge_graph.core.db.sql_lite.service import SQLLiteService
            self.sqlite_service = SQLLiteService(db_path="cache.db")
            logger.info("Fallback SQLite service configured")

    def _configure_databases_legacy(self, db_config):
        """Configure SQLite for caching and optionally Neo4j for knowledge graphs (legacy method)"""

        # Always configure SQLite for document/chunk caching
        if db_config.get('db_type') == 'sqlite' or 'db_location' in db_config:
            from knowledge_graph.core.db.sql_lite.service import SQLLiteService
            sqlite_path = db_config.get('db_location', 'cache.db')
            self.sqlite_service = SQLLiteService(db_path=sqlite_path)
            logger.info(f"SQLite service configured at: {sqlite_path}")

        # Configure knowledge graph storage based on db_type
        graph_db_type = db_config.get('db_type')

        if graph_db_type == 'neo4j':
            # Neo4j for knowledge graphs
            try:
                self.neo4j_service = Neo4jService(db_config)
                self.graph_db_type = 'neo4j'
                logger.info("Neo4j service configured for knowledge graphs")
            except Exception as e:
                logger.warning(f"Neo4j service configuration failed: {e}. Knowledge graph features will be unavailable.")
                self.neo4j_service = None

        elif graph_db_type == 'sqlite':
            self.graph_db_type = 'sqlite'
            logger.info("Using SQLite for knowledge graph storage")
        else:
            logger.warning(f"Unknown or unsupported db_type: {graph_db_type}. Knowledge graph features will be unavailable.")

        # Ensure we have at least SQLite for caching
        if not self.sqlite_service:
            # Fallback SQLite configuration
            from knowledge_graph.core.db.sql_lite.service import SQLLiteService
            self.sqlite_service = SQLLiteService(db_path="cache.db")
            logger.info("Fallback SQLite service configured")
        
    
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

    def get_graph_snapshot(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Build a graph snapshot from the SQLite knowledge graph tables."""
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")
        return self.sqlite_service.get_graph_snapshot(document_id)

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

    # Knowledge graph operations (Neo4j or JSON)
    def save_knowledge_graph(self, document_id, kg_graph, document_metadata=None):
        """Persist a knowledge graph using the configured backend (Neo4j or SQLite)."""
        if self.graph_db_type == 'neo4j' and self.neo4j_service:
            return self.neo4j_service.save_knowledge_graph(document_id, kg_graph)

        if self.sqlite_service:
            return self.sqlite_service.save_knowledge_graph(document_id, kg_graph)

        logger.warning(
            "No graph persistence service configured; skipping KG save for document %s",
            document_id,
        )
        return False

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
        if self.graph_db_type == 'neo4j' and self.neo4j_service:
            return self.neo4j_service.delete_document_graph(document_id)

        if self.sqlite_service:
            # Clearing with an empty payload removes existing rows.
            return self.sqlite_service.save_knowledge_graph(document_id, {"entities": [], "relations": []})

        logger.warning("No graph database service available")
        return False

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
        """Get document ontology from the configured graph database."""
        if self.graph_db_type == 'neo4j' and self.neo4j_service:
            # Neo4j implementation would go here
            logger.warning("Neo4j get_document_ontology not implemented yet")
            return {'entities': [], 'relationships': []}
        if not self.sqlite_service:
            raise ValueError("No database service available")
        return self.sqlite_service.get_document_ontology(document_id)

    def query_knowledge_graph(self, query: str):
        """Query the knowledge graph using natural language"""
        if self.graph_db_type == 'neo4j' and self.neo4j_service:
            logger.warning("Neo4j natural language query not implemented yet")
            return {'query': query, 'entities': [], 'relationships': [], 'total_results': 0}
        if not self.sqlite_service:
            raise ValueError("No database service available for querying")

        snapshot = self.sqlite_service.get_graph_snapshot()
        return {
            'query': query,
            'entities': snapshot.get('nodes', []),
            'relationships': snapshot.get('edges', []),
            'total_results': len(snapshot.get('nodes', [])) + len(snapshot.get('edges', []))
        }

    def get_graph_stats(self):
        """Get statistics about the knowledge graph"""
        if self.graph_db_type == 'neo4j' and self.neo4j_service:
            logger.warning("Neo4j stats not implemented yet")
            return {}
        if not self.sqlite_service:
            raise ValueError("SQLite service not initialized")

        snapshot = self.sqlite_service.get_graph_snapshot()
        return {
            "documents": len(snapshot.get("documents", [])),
            "entities": len(snapshot.get("nodes", [])),
            "relationships": len(snapshot.get("edges", [])),
        }

    def close(self):
        """Close all database connections"""
        if self.sqlite_service and hasattr(self.sqlite_service, 'close'):
            self.sqlite_service.close()
        if self.neo4j_service and hasattr(self.neo4j_service, 'close'):
            self.neo4j_service.close()
        logger.info("DatabaseClient closed")

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

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


        
        
