from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List

from knowledge_graph.data_structs.knowledge_base import KnowledgeBase


class KnowledgeBaseRepository(ABC):
    """Port for managing knowledge base namespaces.

    Implementations persist KnowledgeBase rows and enforce uniqueness of
    (owner_id, slug). Methods should be idempotent where noted.
    """

    @abstractmethod
    def create(self, name: str, slug: str, *, owner_id: Optional[str] = None, description: Optional[str] = None) -> KnowledgeBase:
        """Create a knowledge base. Idempotent on (owner_id, slug)."""

    @abstractmethod
    def get_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        """Fetch a knowledge base by its primary identifier."""

    @abstractmethod
    def get_by_slug(self, slug: str, *, owner_id: Optional[str] = None) -> Optional[KnowledgeBase]:
        """Fetch a knowledge base by slug (optionally scoped by owner)."""

    @abstractmethod
    def list(self, *, owner_id: Optional[str] = None) -> List[KnowledgeBase]:
        """List knowledge bases (optionally filtered by owner)."""

