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
    def __init__(self, db_path: str):
        # Ensure schema via underlying repository
        self._repo = SqlLiteRepository(db_path)
        self.db_path = self._repo.db_path
        self.tabular_document_repository = SQLiteTabularDocumentRepository(db_path)

    def save_document(self, document: Document) -> bool:
        if document.file_type == "csv":
            return self._repo.save_csv_profile(document)
        else:
            return self._repo.save_document(document)
    
    def update_document(self, document: Document) -> bool:
        return self._repo.update_document(document)

    def delete_document(self, document_id: str) -> bool:
        return self._repo.delete_document(document_id)
    
    def list_documents(self, *, kb_id: Optional[str] = None) -> List[str]:
        # Current schema has no kb_id; return all document IDs
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT document_id FROM documents ORDER BY updated_at DESC"
            ).fetchall()
        return [r[0] for r in rows]
