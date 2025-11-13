from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, Any


class EntityResolutionRepository(ABC):
    """Port for entity resolution persistence and queries."""

    @abstractmethod
    def ensure_schema(self) -> None:
        """Create ER-related tables if they do not exist."""

    @abstractmethod
    def fetch_mentions(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Any]:
        """Fetch raw mention rows (implementation-defined DTOs)."""

    @abstractmethod
    def fetch_relationships(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Tuple]:
        """Fetch raw relationship rows for resolution."""

    @abstractmethod
    def upsert_resolved_entities(self, items: List[Any]) -> int:
        """Upsert resolved entities; returns affected row count."""

    @abstractmethod
    def upsert_entity_resolution_map(self, mappings: List[Tuple[str, str, str, str, float]]) -> int:
        """Upsert entity→resolved mappings."""

    @abstractmethod
    def insert_resolved_relationship_mentions(self, rows: List[Tuple[str, str, str, Optional[int], Optional[str], Optional[int]]]) -> None:
        """Insert resolved relationship mention rows (idempotent on unique keys)."""

    @abstractmethod
    def upsert_resolved_relationships_base(self, rows: List[Tuple[str, str, str, str, Optional[str], Optional[str]]]) -> int:
        """Upsert resolved relationships aggregate base rows."""

