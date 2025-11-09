from __future__ import annotations

"""SQLite implementation scaffold for DocumentRepository.

This adapter will delegate to the existing SqlLiteRepository to persist
documents and chunks. For now it is a scaffold with method stubs.
"""

from typing import Optional, List
from knowledge_graph.ports.document_repository import DocumentRepository
from knowledge_graph.document.models.document import Document


class SQLiteDocumentRepository(DocumentRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_document(self, document: Document) -> bool:
        # TODO: Call SqlLiteRepository.save_document(document)
        raise NotImplementedError

    def get_document(self, document_id: str) -> Optional[Document]:
        # TODO: Rehydrate Document from SqlLiteRepository.retrieve_document
        raise NotImplementedError

    def delete_document(self, document_id: str) -> bool:
        # TODO: Delegate to SqlLiteRepository.delete_document
        raise NotImplementedError

    def list_documents(self, *, kb_id: Optional[str] = None) -> List[str]:
        # TODO: Query documents table (optionally filtered by kb_id) and return IDs
        raise NotImplementedError

