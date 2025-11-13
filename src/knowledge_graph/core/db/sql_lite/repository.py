import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
import json
import uuid
import logging
from .queries import (
    CREATE_DOCUMENT_TABLE,
    CREATE_CHUNK_TABLE,
    CREATE_ENTITY_TABLE,
    CREATE_RELATIONSHIP_TABLE,
    CREATE_DOCUMENT_ONTOLOGY_TABLE,
    SAVE_DOCUMENT,
    SAVE_CHUNK,
    SAVE_ENTITY,
    SAVE_RELATIONSHIP,
    SAVE_DOCUMENT_ONTOLOGY,
    DOCUMENT_EXISTS_QUERY,
    GET_DOCUMENT_DATA,
    GET_CHUNK_DATA,
    GET_ENTITIES_BY_DOCUMENT,
    GET_RELATIONSHIPS_BY_DOCUMENT,
    GET_ENTITIES_BY_CHUNK,
    GET_RELATIONSHIPS_BY_CHUNK
)

logger = logging.getLogger(__name__)


class SqlLiteRepository:
    """Handles SQL operations for documents and chunks"""

    def __init__(self, db_path=None):
        # Set default path in project's data directory
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            db_path = project_root / "data" / "document_db.db"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = str(db_path)
        logger.info("Using database at: %s", self.db_path)
        # Don't initialize immediately - make it lazy
        self._initialized = False

    def _ensure_initialized(self):
        """Lazy initialization - only initialize database when first needed."""
        if not self._initialized:
            self._initialize_database()
            self._initialized = True

    def _initialize_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(CREATE_DOCUMENT_TABLE)
                cursor.execute(CREATE_CHUNK_TABLE)
                cursor.execute(CREATE_ENTITY_TABLE)
                cursor.execute(CREATE_RELATIONSHIP_TABLE)
                cursor.execute(CREATE_DOCUMENT_ONTOLOGY_TABLE)
                conn.commit()
                logger.info("Database initialized successfully")
        except Exception as e:
            logger.error("Error initializing database: %s", e)
            raise

    def doc_exists(self, document_id: str) -> bool:  
        """Check if the document exists"""
        self._ensure_initialized()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Try document_id first
                cursor.execute(DOCUMENT_EXISTS_QUERY, (document_id,))  
                result = cursor.fetchone()
                
                # If not found, try file_path as fallback
                if result is None:
                    cursor.execute("SELECT * FROM documents WHERE file_path = ?", (document_id,))
                    result = cursor.fetchone()
                    
                return result is not None
        except Exception as e:
            logger.error("Error checking if document exists: %s", e)
            return False

    def save_document(self, document: Any) -> bool:
        """Save document and its chunks to the database"""
        self._ensure_initialized()
        try:
            timestamp = datetime.now()
            
            # Debug information
            self._print_debug_info(document, timestamp)
            logger.info("Attempting to save document: %s", document.file_path)
            logger.debug("Database path: %s", self.db_path)

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                try:
                    # Start transaction
                    cursor.execute("BEGIN TRANSACTION")
                    logger.debug("Started database transaction")
                    
                    # Save document and get its ID
                    doc_values = (
                        document.id,
                        document.file_path,
                        document.hash if hasattr(document, 'hash') else None,
                        document.file_type,
                        document.title,
                        document.metadata.summary if hasattr(document.metadata, 'summary') else None,
                        document.raw_content,
                        document.clean_content,
                        timestamp,
                        timestamp,
                        timestamp
                    )
                    
                    logger.debug("Saving document with values: %s", doc_values)
                    cursor.execute(SAVE_DOCUMENT, doc_values)
                    document_id = cursor.fetchone()[0]  # Get the returned ID
                    logger.info("Saved document with ID: %s", document_id)
                    
                    # Delete existing chunks for this document
                    cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                    logger.debug("Deleted existing chunks for document %s", document_id)
                    
                    # Save chunks
                    chunk_ids = []  # Store chunk IDs for linking
                    if hasattr(document, 'textChunks') and document.textChunks:
                        logger.info("Saving %d chunks", len(document.textChunks))
                        for i, chunk in enumerate(document.textChunks):
                            chunk_values = (
                                document_id,
                                chunk.content,
                                i,  # chunk_index
                                chunk.metadata.word_count,
                                chunk.metadata.token_count if hasattr(chunk.metadata, 'token_count') else None,
                                chunk.metadata.language,
                                json.dumps(chunk.metadata.topics) if chunk.metadata.topics else None,
                                json.dumps(chunk.metadata.keywords) if chunk.metadata.keywords else None,
                                chunk.metadata.start_index,
                                chunk.metadata.end_index,
                                None,  # previous_chunk_id - will be updated
                                None   # next_chunk_id - will be updated
                            )
                            logger.debug("Saving chunk %d with values: %s", i, chunk_values)
                            cursor.execute(SAVE_CHUNK, chunk_values)
                            chunk_ids.append(cursor.lastrowid)
                            logger.debug("Saved chunk with ID: %s", cursor.lastrowid)
                    else:
                        logger.warning("No chunks found in document")
                    
                    # Update chunk links
                    if len(chunk_ids) > 1:
                        logger.debug("Updating chunk links")
                        for i, chunk_id in enumerate(chunk_ids):
                            prev_id = chunk_ids[i-1] if i > 0 else None
                            next_id = chunk_ids[i+1] if i < len(chunk_ids)-1 else None
                            
                            cursor.execute("""
                                UPDATE chunks 
                                SET previous_chunk_id = ?, next_chunk_id = ?
                                WHERE id = ?
                            """, (prev_id, next_id, chunk_id))
                    
                    kg_data = getattr(document, "knowledge_graph", {}) or {}
                    self._write_knowledge_graph(cursor, document_id, kg_data)

                    # Commit transaction
                    conn.commit()
                    logger.info("Document, chunks, and KG saved successfully")
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    logger.error("Error during save, rolling back: %s", e)
                    raise e
                
        except sqlite3.Error as e:
            logger.error("SQLite error: %s", str(e))
            raise
        except Exception as e:
            logger.error("Unexpected error: %s", str(e))
            raise

    def retrieve_document(self, document_id: str) -> Optional[Dict]:
        """Get document and its chunks from the database"""
        self._ensure_initialized()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if we're using the new schema with document_id
                cursor.execute("PRAGMA table_info(documents)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                # Determine which column to use for lookup
                if 'document_id' in column_names:
                    # Use document_id field
                    cursor.execute(GET_DOCUMENT_DATA, (document_id,))
                    document_data = cursor.fetchall()
                    cursor.execute(GET_CHUNK_DATA, (document_id,))
                    chunk_data = cursor.fetchall()
                else:
                    # Fall back to using file_path for older schema
                    logger.warning("Using legacy schema without document_id column")
                    cursor.execute("SELECT * FROM documents WHERE file_path = ?", (document_id,))
                    document_data = cursor.fetchall()
                    if document_data:
                        cursor.execute("SELECT * FROM chunks WHERE document_id = ?", (document_data[0][0],))
                        chunk_data = cursor.fetchall()
                    else:
                        chunk_data = []
                
                data = {'document': document_data, 'chunks': chunk_data}
                return data
                
        except Exception as e:
            logger.error("Error retrieving document: %s", e)
            return None
        
    def delete_document(self, document_id: str) -> bool:
        """Delete document by ID"""
        self._ensure_initialized()
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
                
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")

            cursor.execute("DELETE FROM relationships WHERE document_id = ?", (document_id,))
            cursor.execute("DELETE FROM entities WHERE document_id = ?", (document_id,))
            cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            logger.info("Deleted KG rows and chunks for document %s", document_id)
                
            # Then delete the document
            cursor.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
                
            # Commit changes
            conn.commit()
            logger.info("Document and all associated chunks deleted with ID: %s", document_id)
            return True
                
        except Exception as e:
            # Rollback on error
            if conn:
                conn.rollback()
            logger.error("Error deleting document: %s", e)
            return False
        finally:
            # Close connection if it was opened
            if conn:
                conn.close()

    def _write_knowledge_graph(self, cursor, document_id: str, kg_data: Dict[str, Any]) -> None:
        """Persist entities and relationships for a document using an open cursor."""
        cursor.execute("DELETE FROM relationships WHERE document_id = ?", (document_id,))
        cursor.execute("DELETE FROM entities WHERE document_id = ?", (document_id,))
        logger.debug("Deleted previous KG entries for document %s", document_id)

        entities = kg_data.get("entities") or []
        relations = kg_data.get("relations") or []

        entity_ids: Dict[str, str] = {}
        for entity in entities:
            if isinstance(entity, str):
                name = entity
            elif isinstance(entity, dict):
                name = entity.get("name") or entity.get("label") or str(entity)
            else:
                name = str(entity)

            normalized = name.strip()
            if not normalized:
                continue

            entity_id = f"{document_id}::{normalized.lower()}"
            entity_ids[normalized] = entity_id

            entity_values = (
                entity_id,
                normalized,
                "extracted",
                "general",
                document_id,
                None,
            )
            cursor.execute(SAVE_ENTITY, entity_values)

        relation_count = 0
        for relation in relations:
            if isinstance(relation, dict):
                source = relation.get("source") or relation.get("subject")
                predicate = relation.get("relation") or relation.get("predicate")
                target = relation.get("target") or relation.get("object")
            elif isinstance(relation, (list, tuple)) and len(relation) >= 3:
                source, predicate, target = relation[:3]
            else:
                continue

            if not predicate:
                continue

            source_name = str(source).strip()
            target_name = str(target).strip()
            if not source_name or not target_name:
                continue

            source_id = entity_ids.get(source_name) or f"{document_id}::{source_name.lower()}"
            target_id = entity_ids.get(target_name) or f"{document_id}::{target_name.lower()}"
            relation_id = f"{document_id}::{relation_count}"
            relation_count += 1

            relation_values = (
                relation_id,
                source_id,
                target_id,
                str(predicate).strip(),
                None,
                document_id,
                None,
            )
            cursor.execute(SAVE_RELATIONSHIP, relation_values)

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any]) -> bool:
        """Public wrapper to persist a document-level knowledge graph payload."""
        self._ensure_initialized()
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("BEGIN TRANSACTION")
            self._write_knowledge_graph(cursor, document_id, kg_data or {})
            conn.commit()
            logger.info("Knowledge graph saved for document %s", document_id)
            return True
        except Exception as exc:
            if conn:
                conn.rollback()
            logger.error("Error saving knowledge graph for %s: %s", document_id, exc)
            return False
        finally:
            if conn:
                conn.close()

    def save_document_ontology(self, document_id: str, ontology: Any) -> bool:
        """Save ontology to document"""
        self._ensure_initialized()
        try:
            # Serialize ontology to JSON if needed
            ontology_json = json.dumps(ontology) if isinstance(ontology, dict) else json.dumps(ontology.dict())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(SAVE_DOCUMENT_ONTOLOGY, (document_id, ontology_json))
                conn.commit()
                logger.info("Saved ontology for document: %s", document_id)
                return True
        except Exception as e:
            logger.error("Error saving document ontology: %s", e)
            return False
                
    def save_entities_and_relationships(self, document_id: str, chunk_id: Optional[int], ontology: Any) -> bool:
        """Save entities and relationships extracted from ontology"""
        self._ensure_initialized()
        try:
            logger.info("Saving ontology for document: %s", document_id)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                try:
                    # Start transaction
                    cursor.execute("BEGIN TRANSACTION")
                    logger.debug("Started ontology transaction")
                    
                    # Process entities
                    entity_ids = {}  # Map entity names to IDs for relationship creation
                    
                    if hasattr(ontology, 'entities'):
                        entities = ontology.entities
                    elif isinstance(ontology, dict) and 'entities' in ontology:
                        entities = ontology['entities']
                    else:
                        entities = []
                    
                    logger.debug("Processing %d entities", len(entities))
                    
                    for entity in entities:
                        # Extract entity data
                        if hasattr(entity, 'name'):
                            name = entity.name
                            entity_type = entity.type
                            category = entity.category
                        else:
                            name = entity['name']
                            entity_type = entity['type']
                            category = entity['category']
                        
                        # Generate unique ID for entity
                        entity_id = str(uuid.uuid4())
                        entity_ids[name] = entity_id
                        
                        # Save entity
                        cursor.execute(SAVE_ENTITY, (
                            entity_id,
                            name,
                            entity_type,
                            category,
                            document_id,
                            chunk_id
                        ))
                        logger.debug("Saved entity: %s (%s/%s)", name, entity_type, category)
                    
                    # Process relationships
                    relationships = []
                    
                    if isinstance(ontology, dict):
                        if 'relationships' in ontology:
                            relationships = ontology['relationships']
                    elif hasattr(ontology, 'relationships'):
                        relationships = ontology.relationships
                    
                    logger.debug("Processing %d relationships", len(relationships))
                    
                    for relationship in relationships:
                        # Extract relationship data
                        if hasattr(relationship, 'source'):
                            source = relationship.source
                            target = relationship.target
                            relation = relationship.relation
                            context = relationship.context
                        else:
                            source = relationship['source']
                            target = relationship['target']
                            relation = relationship['relation']
                            context = relationship['context']
                        
                        # Get entity IDs
                        source_entity_id = entity_ids.get(source)
                        target_entity_id = entity_ids.get(target)
                        
                        # Skip if either entity doesn't exist
                        if not source_entity_id or not target_entity_id:
                            logger.warning("Skipping relationship: %s → %s → %s (missing entity)", source, relation, target)
                            continue
                        
                        # Generate unique ID for relationship
                        relationship_id = str(uuid.uuid4())
                        
                        # Save relationship
                        cursor.execute(SAVE_RELATIONSHIP, (
                            relationship_id,
                            source_entity_id,
                            target_entity_id,
                            relation,
                            context,
                            document_id,
                            chunk_id
                        ))
                        logger.debug("Saved relationship: %s → %s → %s", source, relation, target)
                    
                    # Commit transaction
                    conn.commit()
                    logger.info("Ontology saved successfully")
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    logger.error("Error saving ontology: %s", e)
                    return False
                
        except Exception as e:
            logger.error("Error connecting to database: %s", e)
            return False

    def get_document_ontology(self, document_id: str) -> Dict:
        """Get all entities and relationships for a document"""
        self._ensure_initialized()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get entities
                cursor.execute(GET_ENTITIES_BY_DOCUMENT, (document_id,))
                entity_rows = cursor.fetchall()
                
                # Get relationships with entity details
                cursor.execute(GET_RELATIONSHIPS_BY_DOCUMENT, (document_id,))
                relationship_rows = cursor.fetchall()
                
                # Format response
                entities = []
                for row in entity_rows:
                    entity = {
                        'entity_id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'category': row[3],
                        'document_id': row[4],
                        'chunk_id': row[5],
                        'created_at': row[6]
                    }
                    entities.append(entity)
                
                relationships = []
                for row in relationship_rows:
                    relationship = {
                        'relationship_id': row[0],
                        'source_entity_id': row[1],
                        'target_entity_id': row[2],
                        'relation': row[3],
                        'context': row[4],
                        'document_id': row[5],
                        'chunk_id': row[6],
                        'created_at': row[7],
                        'source_name': row[8],
                        'source_type': row[9],
                        'source_category': row[10],
                        'target_name': row[11],
                        'target_type': row[12],
                        'target_category': row[13]
                    }
                    relationships.append(relationship)
                
                return {
                    'entities': entities,
                    'relationships': relationships
                }
                
        except Exception as e:
            logger.error("Error retrieving ontology: %s", e)
            return {'entities': [], 'relationships': []}

    def get_graph_snapshot(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Build a graph snapshot using SQLite entities/relationships tables."""
        self._ensure_initialized()
        snapshot = {"nodes": [], "edges": [], "documents": []}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                # Documents
                if document_id:
                    cursor.execute(
                        "SELECT document_id, title, document_type, created_at, updated_at, last_modified FROM documents WHERE document_id = ?",
                        (document_id,)
                    )
                else:
                    cursor.execute(
                        "SELECT document_id, title, document_type, created_at, updated_at, last_modified FROM documents"
                    )
                documents = []
                doc_ids = set()
                for row in cursor.fetchall():
                    doc = {
                        "id": row[0],
                        "title": row[1] or row[0],
                        "source": "local",
                        "mimeType": row[2],
                        "status": "ready",
                        "description": None,
                        "author": None,
                        "externalId": None,
                        "url": None,
                        "createdAt": row[3],
                        "updatedAt": row[4] or row[5],
                    }
                    documents.append(doc)
                    doc_ids.add(row[0])
                snapshot["documents"] = documents

                params = (document_id,) if document_id else tuple()

                # Entities
                entity_query = "SELECT entity_id, name, type, category, document_id, chunk_id, created_at FROM entities"
                if document_id:
                    entity_query += " WHERE document_id = ?"
                cursor.execute(entity_query, params)
                nodes = []
                for row in cursor.fetchall():
                    node = {
                        "id": row[0],
                        "label": row[1],
                        "type": row[2] or row[3] or "concept",
                        "description": row[3],
                        "provenance": None,
                        "documents": [row[4]] if row[4] else [],
                        "triples": [],
                        "createdAt": row[6],
                        "updatedAt": row[6],
                    }
                    nodes.append(node)
                    if row[4]:
                        doc_ids.add(row[4])
                snapshot["nodes"] = nodes

                # Relationships
                relationship_query = (
                    "SELECT relationship_id, source_entity_id, target_entity_id, relation, context, document_id, chunk_id, created_at "
                    "FROM relationships"
                )
                if document_id:
                    relationship_query += " WHERE document_id = ?"
                cursor.execute(relationship_query, params)
                edges = []
                for row in cursor.fetchall():
                    edge = {
                        "id": row[0],
                        "source": row[1],
                        "target": row[2],
                        "predicate": row[3],
                        "description": row[4],
                        "confidence": None,
                        "sourceDocumentId": row[5],
                        "createdAt": row[7],
                        "updatedAt": row[7],
                    }
                    edges.append(edge)
                    if row[5]:
                        doc_ids.add(row[5])
                snapshot["edges"] = edges

                return snapshot

        except Exception as exc:
            logger.error("Error building graph snapshot: %s", exc)
            return snapshot

    def get_chunk_ontology(self, chunk_id: int) -> Dict:
        """Get all entities and relationships for a chunk"""
        self._ensure_initialized()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get entities
                cursor.execute(GET_ENTITIES_BY_CHUNK, (chunk_id,))
                entity_rows = cursor.fetchall()
                
                # Get relationships with entity details
                cursor.execute(GET_RELATIONSHIPS_BY_CHUNK, (chunk_id,))
                relationship_rows = cursor.fetchall()
                
                # Format response
                entities = []
                for row in entity_rows:
                    entity = {
                        'entity_id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'category': row[3],
                        'document_id': row[4],
                        'chunk_id': row[5],
                        'created_at': row[6]
                    }
                    entities.append(entity)
                
                relationships = []
                for row in relationship_rows:
                    relationship = {
                        'relationship_id': row[0],
                        'source_entity_id': row[1],
                        'target_entity_id': row[2],
                        'relation': row[3],
                        'context': row[4],
                        'document_id': row[5],
                        'chunk_id': row[6],
                        'created_at': row[7],
                        'source_name': row[8],
                        'source_type': row[9],
                        'source_category': row[10],
                        'target_name': row[11],
                        'target_type': row[12],
                        'target_category': row[13]
                    }
                    relationships.append(relationship)
                
                return {
                    'entities': entities,
                    'relationships': relationships
                }
                
        except Exception as e:
            logger.error("Error retrieving chunk ontology: %s", e)
            return {'entities': [], 'relationships': []}

    def _print_debug_info(self, document: Any, timestamp: datetime) -> None:
        """Log debug information about the document"""
        try:
            info = {
                "path": repr(getattr(document, 'file_path', '')),
                "type": repr(getattr(document, 'file_type', '')),
                "title": repr(getattr(document, 'title', '')),
                "chunks": len(getattr(document, 'textChunks', []) or []),
                "created_at": str(timestamp),
                "updated_at": str(timestamp),
                "last_modified": str(timestamp),
            }
            logger.debug("-- Debug - Saving Document: %s", info)
        except Exception:
            # Defensive: avoid logging failures impacting main flow
            logger.debug("-- Debug - Saving Document: <unavailable>")

    def query(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        """Execute a custom query"""
        self._ensure_initialized()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                results = cursor.fetchall()
                return results
        except Exception as e:
            logger.error("Error executing query: %s", e)
            raise
