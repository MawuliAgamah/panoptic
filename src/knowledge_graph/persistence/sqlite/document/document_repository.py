from __future__ import annotations

"""SQLite implementation scaffold for DocumentRepository.

This adapter will delegate to the existing SqlLiteRepository to persist
documents and chunks. For now it is a scaffold with method stubs.
"""

from typing import Optional, List
from ....ports.document_repository import DocumentRepository
from ....data_structs.document import Document
from ....core.db.sql_lite.repository import SqlLiteRepository
from ....core.db.db_client import DatabaseClient
import sqlite3

class SQLiteDocumentRepository(DocumentRepository):
    """SQLite implementation of DocumentRepository port."""
    
    def __init__(self, db_path: str, shared_repo=None):
        # Use shared repository if provided, otherwise create new one
        if shared_repo:
            self._repo = shared_repo
        else:
            self._repo = SqlLiteRepository(db_path)
        self.db_path = self._repo.db_path

    def create_tables(self) -> bool:
        """Ensure tables are initialized."""
        self._repo._ensure_initialized()
        return True

    def save_document(self, document: Document) -> bool:
        """Insert or update a document (and associated chunks if present)."""
        return self._repo.save_document(document)

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by its identifier."""
        return self._repo.retrieve_document(document_id)
    
    def update_document(self, document: Document) -> bool:
        """Update an existing document."""
        # save_document uses INSERT ... ON CONFLICT DO UPDATE, so it handles updates
        return self._repo.save_document(document)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its related rows."""
        return self._repo.delete_document(document_id)
    
    def list_documents(self, *, kb_id: Optional[str] = None) -> List[str]:
        """List document identifiers (optionally filtered by knowledge base)."""
        # Ensure database is initialized
        self._repo._ensure_initialized()
        # Current schema has no kb_id; return all document IDs
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT document_id FROM documents ORDER BY updated_at DESC"
            ).fetchall()
        return [r[0] for r in rows]
