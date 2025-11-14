from __future__ import annotations

"""SQLite implementation for GraphRepository.

This adapter implements direct SQL operations for persisting and querying
knowledge graphs without relying on a shared repository.
"""

from typing import Optional, Dict, Any
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

from ....ports.graph_repository import GraphRepository
from ..core.queries import (
    CREATE_ENTITIES_TABLE,
    CREATE_RELATIONSHIPS_TABLE,
    CREATE_INDEX_ENTITIES_KB_ID,
    CREATE_INDEX_ENTITIES_DOCUMENT_ID,
    CREATE_INDEX_ENTITIES_DEFINITION_ID,
    CREATE_INDEX_ENTITIES_TYPE,
    CREATE_INDEX_ENTITIES_TYPE_LABEL,
    CREATE_INDEX_RELATIONSHIPS_KB_ID,
    CREATE_INDEX_RELATIONSHIPS_DOCUMENT_ID,
    CREATE_INDEX_RELATIONSHIPS_SOURCE_ID,
    CREATE_INDEX_RELATIONSHIPS_TARGET_ID,
    CREATE_INDEX_RELATIONSHIPS_TYPE,
    CREATE_INDEX_RELATIONSHIPS_DEFINITION_ID,
)

logger = logging.getLogger(__name__)


class SQLiteGraphRepository(GraphRepository):
    """SQLite implementation of GraphRepository port."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
    
    def _ensure_db_dir(self) -> None:
        """Ensure the database directory exists."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    def create_tables(self) -> bool:
        """Ensure tables are initialized."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                
                # Create entities table
                cur.execute(CREATE_ENTITIES_TABLE)
                cur.execute(CREATE_INDEX_ENTITIES_KB_ID)
                cur.execute(CREATE_INDEX_ENTITIES_DOCUMENT_ID)
                cur.execute(CREATE_INDEX_ENTITIES_DEFINITION_ID)
                cur.execute(CREATE_INDEX_ENTITIES_TYPE)
                cur.execute(CREATE_INDEX_ENTITIES_TYPE_LABEL)
                
                # Create relationships table
                cur.execute(CREATE_RELATIONSHIPS_TABLE)
                cur.execute(CREATE_INDEX_RELATIONSHIPS_KB_ID)
                cur.execute(CREATE_INDEX_RELATIONSHIPS_DOCUMENT_ID)
                cur.execute(CREATE_INDEX_RELATIONSHIPS_SOURCE_ID)
                cur.execute(CREATE_INDEX_RELATIONSHIPS_TARGET_ID)
                cur.execute(CREATE_INDEX_RELATIONSHIPS_TYPE)
                cur.execute(CREATE_INDEX_RELATIONSHIPS_DEFINITION_ID)
                
                conn.commit()
                logger.info("Graph tables created/verified")
                return True
        except Exception as e:
            logger.error(f"Error creating graph tables: {e}")
            return False

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any], *, kb_id: Optional[str] = None) -> bool:
        """Persist a document-level knowledge graph payload."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                
                # Convert IDs to integers
                try:
                    doc_id_int = int(document_id)
                except (ValueError, TypeError):
                    doc_id_int = abs(hash(document_id)) % (10 ** 9)
                
                kb_id_int = 0
                if kb_id:
                    try:
                        kb_id_int = int(kb_id)
                    except (ValueError, TypeError):
                        kb_id_int = 0
                
                # Extract entities and relationships from kg_data
                entities = kg_data.get('entities', [])
                relationships = kg_data.get('relationships', [])
                
                # Delete existing entities and relationships for this document
                cur.execute("DELETE FROM relationships WHERE document_id = ?", (doc_id_int,))
                cur.execute("DELETE FROM entities WHERE document_id = ?", (doc_id_int,))
                
                # Insert entities
                entity_id_map = {}  # Map from entity ID in kg_data to database ID
                for idx, entity in enumerate(entities):
                    entity_id = entity.get('id') or f"entity_{idx}"
                    entity_type = entity.get('type', 'concept')
                    entity_label = entity.get('label', entity_id)
                    properties = json.dumps(entity.get('properties', {}))
                    
                    # Use hash of entity_id for database ID
                    entity_db_id = abs(hash(entity_id)) % (10 ** 9)
                    entity_id_map[entity_id] = entity_db_id
                    
                    cur.execute(
                        """INSERT INTO entities (
                            id, kb_id, document_id, entity_definition_id, entity_type, entity_label, properties
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            entity_db_id,
                            kb_id_int,
                            doc_id_int,
                            0,  # entity_definition_id - default to 0
                            entity_type,
                            entity_label,
                            properties,
                        )
                    )
                
                # Insert relationships
                for rel in relationships:
                    source_id = rel.get('source')
                    target_id = rel.get('target')
                    rel_type = rel.get('predicate') or rel.get('type', 'related_to')
                    properties = json.dumps(rel.get('properties', {}))
                    confidence = rel.get('confidence', rel.get('weight'))
                    
                    # Get database entity IDs
                    source_db_id = entity_id_map.get(source_id)
                    target_db_id = entity_id_map.get(target_id)
                    
                    if source_db_id and target_db_id:
                        rel_db_id = abs(hash(f"{source_id}_{target_id}_{rel_type}")) % (10 ** 9)
                        cur.execute(
                            """INSERT INTO relationships (
                                id, kb_id, document_id, relationship_definition_id, relationship_type,
                                source_entity_id, target_entity_id, properties, confidence_score
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                rel_db_id,
                                kb_id_int,
                                doc_id_int,
                                None,  # relationship_definition_id
                                rel_type,
                                source_db_id,
                                target_db_id,
                                properties,
                                confidence,
                            )
                        )
                
                conn.commit()
                logger.debug(f"Knowledge graph saved for document: {document_id}")
                return True
        except Exception as e:
            logger.error(f"Error saving knowledge graph for document {document_id}: {e}")
            return False

    def get_graph_snapshot(self, *, kb_id: Optional[str] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a node/edge/documents snapshot filtered by kb and/or document."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                
                # Build WHERE clause
                where_clauses = []
                params = []
                
                if kb_id:
                    try:
                        kb_id_int = int(kb_id)
                        where_clauses.append("e.kb_id = ?")
                        params.append(kb_id_int)
                    except (ValueError, TypeError):
                        pass
                
                if document_id:
                    try:
                        doc_id_int = int(document_id)
                        where_clauses.append("e.document_id = ?")
                        params.append(doc_id_int)
                    except (ValueError, TypeError):
                        doc_id_int = abs(hash(document_id)) % (10 ** 9)
                        where_clauses.append("e.document_id = ?")
                        params.append(doc_id_int)
                
                where_sql = "WHERE " + " AND ".join(where_clauses) if where_clauses else ""
                
                # Fetch entities (nodes)
                nodes_query = f"""
                    SELECT DISTINCT
                        e.id, e.entity_label, e.entity_type, e.properties,
                        e.document_id, e.kb_id
                    FROM entities e
                    {where_sql}
                """
                cur.execute(nodes_query, params)
                entity_rows = cur.fetchall()
                
                nodes = []
                entity_id_to_node = {}
                for row in entity_rows:
                    node_id = str(row[0])
                    properties = json.loads(row[3]) if row[3] else {}
                    node = {
                        "id": node_id,
                        "label": row[1] or node_id,
                        "type": row[2] or "concept",
                        "properties": properties,
                        "document_id": str(row[4]) if row[4] else None,
                        "kb_id": str(row[5]) if row[5] else None,
                    }
                    nodes.append(node)
                    entity_id_to_node[row[0]] = node
                
                # Fetch relationships (edges)
                rel_where_clauses = []
                if kb_id:
                    try:
                        kb_id_int = int(kb_id)
                        rel_where_clauses.append("r.kb_id = ?")
                    except (ValueError, TypeError):
                        pass
                
                if document_id:
                    try:
                        doc_id_int = int(document_id)
                        rel_where_clauses.append("r.document_id = ?")
                    except (ValueError, TypeError):
                        doc_id_int = abs(hash(document_id)) % (10 ** 9)
                        rel_where_clauses.append("r.document_id = ?")
                
                rel_where_sql = "WHERE " + " AND ".join(rel_where_clauses) if rel_where_clauses else ""
                
                edges_query = f"""
                    SELECT DISTINCT
                        r.id, r.relationship_type, r.source_entity_id, r.target_entity_id,
                        r.properties, r.confidence_score, r.document_id, r.kb_id
                    FROM relationships r
                    {rel_where_sql}
                """
                cur.execute(edges_query, params)
                rel_rows = cur.fetchall()
                
                edges = []
                for row in rel_rows:
                    edge = {
                        "id": str(row[0]),
                        "source": str(row[2]),
                        "target": str(row[3]),
                        "predicate": row[1] or "related_to",
                        "properties": json.loads(row[4]) if row[4] else {},
                        "confidence": row[5],
                        "document_id": str(row[6]) if row[6] else None,
                        "kb_id": str(row[7]) if row[7] else None,
                    }
                    edges.append(edge)
                
                # Fetch documents
                doc_where_clauses = []
                doc_params = []
                if kb_id:
                    try:
                        kb_id_int = int(kb_id)
                        doc_where_clauses.append("d.kb_id = ?")
                        doc_params.append(kb_id_int)
                    except (ValueError, TypeError):
                        pass
                
                if document_id:
                    try:
                        doc_id_int = int(document_id)
                        doc_where_clauses.append("d.id = ?")
                        doc_params.append(doc_id_int)
                    except (ValueError, TypeError):
                        doc_id_int = abs(hash(document_id)) % (10 ** 9)
                        doc_where_clauses.append("d.id = ?")
                        doc_params.append(doc_id_int)
                
                doc_where_sql = "WHERE " + " AND ".join(doc_where_clauses) if doc_where_clauses else ""
                
                docs_query = f"""
                    SELECT DISTINCT d.id, d.file_name, d.file_path, d.file_type
                    FROM pdf_document d
                    {doc_where_sql}
                """
                cur.execute(docs_query, doc_params)
                doc_rows = cur.fetchall()
                
                documents = []
                for row in doc_rows:
                    documents.append({
                        "id": str(row[0]),
                        "name": row[1] or "",
                        "path": row[2] or "",
                        "type": row[3] or "",
                    })
                
                return {
                    "nodes": nodes,
                    "edges": edges,
                    "documents": documents,
                }
        except Exception as e:
            logger.error(f"Error getting graph snapshot: {e}")
            return {"nodes": [], "edges": [], "documents": []}
