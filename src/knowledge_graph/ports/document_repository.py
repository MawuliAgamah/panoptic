from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List

from knowledge_graph.document.models.document import Document


class DocumentRepository(ABC):
    """Port for persisting and retrieving document records (and chunks).

    Implementations may store full content or only metadata. The contract
    focuses on identifiers and lifecycle operations used by the pipeline.
    """

    @abstractmethod
    def save_document(self, document: Document) -> bool:
        """Insert or update a document (and associated chunks if present)."""

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by its identifier."""

    @abstractmethod
    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its related rows."""

    @abstractmethod
    def list_documents(self, *, kb_id: Optional[str] = None) -> List[str]:
        """List document identifiers (optionally filtered by knowledge base)."""

