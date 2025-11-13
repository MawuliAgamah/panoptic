from __future__ import annotations

"""SQLite implementation for Knowledge Base Ontology persistence.

Manages ontology specifications associated with knowledge bases and documents.
"""

from typing import Optional, List, Dict, Any
import logging
import sqlite3
from datetime import datetime
from .queries import CREATE_KNOWLEDGE_BASE_ONTOLOGIES_TABLE

logger = logging.getLogger(__name__)


class SQLiteKnowledgeBaseOntologyRepository:
    """SQLite implementation for knowledge base ontology persistence."""

    def __init__(self, db_path: str):
        """Initialize repository with database path.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_schema()
        self._logger = logging.getLogger("knowledge_graph.persistence.sqlite.kb_ontology")

    def _ensure_schema(self) -> None:
        """Ensure knowledge_base_ontologies table schema exists."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute(CREATE_KNOWLEDGE_BASE_ONTOLOGIES_TABLE)
            conn.commit()

    def create(
        self,
        kb_id: Optional[int] = None,
        document_id: Optional[int] = None,
        name: Optional[str] = None,
        specification: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        version: int = 1,
    ) -> int:
        """Create a new knowledge base ontology record.
        
        Args:
            kb_id: Knowledge base ID (optional)
            document_id: Document ID (optional)
            name: Ontology name (optional)
            specification: JSON specification (optional)
            status: Status string (optional)
            version: Version number (default: 1)
            
        Returns:
            The ID of the created ontology record
        """
        import json
        
        spec_json = json.dumps(specification) if specification else None
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO knowledge_base_ontologies 
                (kb_id, document_id, name, specification, status, version)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (kb_id, document_id, name, spec_json, status, version),
            )
            conn.commit()
            return cur.lastrowid

    def get_by_id(self, ontology_id: int) -> Optional[Dict[str, Any]]:
        """Get ontology by ID.
        
        Args:
            ontology_id: Ontology record ID
            
        Returns:
            Dictionary with ontology data or None if not found
        """
        import json
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, kb_id, document_id, name, specification, status, version
                FROM knowledge_base_ontologies
                WHERE id = ?
                """,
                (ontology_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            
            spec = None
            if row[4]:
                try:
                    spec = json.loads(row[4])
                except json.JSONDecodeError:
                    spec = row[4]
            
            return {
                "id": row[0],
                "kb_id": row[1],
                "document_id": row[2],
                "name": row[3],
                "specification": spec,
                "status": row[5],
                "version": row[6],
            }

    def get_by_kb_id(self, kb_id: int) -> List[Dict[str, Any]]:
        """Get all ontologies for a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            List of ontology dictionaries
        """
        import json
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, kb_id, document_id, name, specification, status, version
                FROM knowledge_base_ontologies
                WHERE kb_id = ?
                ORDER BY version DESC
                """,
                (kb_id,),
            )
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                spec = None
                if row[4]:
                    try:
                        spec = json.loads(row[4])
                    except json.JSONDecodeError:
                        spec = row[4]
                
                result.append({
                    "id": row[0],
                    "kb_id": row[1],
                    "document_id": row[2],
                    "name": row[3],
                    "specification": spec,
                    "status": row[5],
                    "version": row[6],
                })
            return result

    def get_by_document_id(self, document_id: int) -> List[Dict[str, Any]]:
        """Get all ontologies for a document.
        
        Args:
            document_id: Document ID
            
        Returns:
            List of ontology dictionaries
        """
        import json
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                SELECT id, kb_id, document_id, name, specification, status, version
                FROM knowledge_base_ontologies
                WHERE document_id = ?
                ORDER BY version DESC
                """,
                (document_id,),
            )
            rows = cur.fetchall()
            
            result = []
            for row in rows:
                spec = None
                if row[4]:
                    try:
                        spec = json.loads(row[4])
                    except json.JSONDecodeError:
                        spec = row[4]
                
                result.append({
                    "id": row[0],
                    "kb_id": row[1],
                    "document_id": row[2],
                    "name": row[3],
                    "specification": spec,
                    "status": row[5],
                    "version": row[6],
                })
            return result

    def update(
        self,
        ontology_id: int,
        name: Optional[str] = None,
        specification: Optional[Dict[str, Any]] = None,
        status: Optional[str] = None,
        version: Optional[int] = None,
    ) -> bool:
        """Update an existing ontology record.
        
        Args:
            ontology_id: Ontology record ID
            name: New name (optional)
            specification: New specification (optional)
            status: New status (optional)
            version: New version (optional)
            
        Returns:
            True if update succeeded, False otherwise
        """
        import json
        
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if specification is not None:
            updates.append("specification = ?")
            params.append(json.dumps(specification))
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        if version is not None:
            updates.append("version = ?")
            params.append(version)
        
        if not updates:
            return False
        
        params.append(ontology_id)
        
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE knowledge_base_ontologies SET {', '.join(updates)} WHERE id = ?",
                params,
            )
            conn.commit()
            return cur.rowcount > 0

    def delete(self, ontology_id: int) -> bool:
        """Delete an ontology record.
        
        Args:
            ontology_id: Ontology record ID
            
        Returns:
            True if deletion succeeded, False otherwise
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_base_ontologies WHERE id = ?", (ontology_id,))
            conn.commit()
            return cur.rowcount > 0

    def delete_by_kb_id(self, kb_id: int) -> int:
        """Delete all ontologies for a knowledge base.
        
        Args:
            kb_id: Knowledge base ID
            
        Returns:
            Number of deleted records
        """
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM knowledge_base_ontologies WHERE kb_id = ?", (kb_id,))
            conn.commit()
            return cur.rowcount

