from __future__ import annotations

"""SQLite implementation scaffold for EntityResolutionStore.

This adapter will wrap the helper functions in entity_resolution.persist,
adding kb_id filtering once the schema supports it. For now, it exposes
method stubs with the correct signatures.
"""

from typing import Optional, List, Tuple, Any
from knowledge_graph.ports.entity_resolution_store import EntityResolutionStore


class SQLiteEntityResolutionStore(EntityResolutionStore):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def ensure_schema(self) -> None:
        # TODO: Call ensure_schema on a DatabaseClient configured with db_path
        raise NotImplementedError

    def fetch_mentions(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Any]:
        # TODO: Delegate to persist.fetch_mentions with kb_id support later
        raise NotImplementedError

    def fetch_relationships(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Tuple]:
        # TODO: Delegate to persist.fetch_relationships with kb_id support later
        raise NotImplementedError

    def upsert_resolved_entities(self, items: List[Any]) -> int:
        # TODO: Delegate to persist.upsert_resolved_entities
        raise NotImplementedError

    def upsert_entity_resolution_map(self, mappings: List[Tuple[str, str, str, str, float]]) -> int:
        # TODO: Delegate to persist.upsert_entity_resolution_map
        raise NotImplementedError

    def insert_resolved_relationship_mentions(self, rows: List[Tuple[str, str, str, Optional[int], Optional[str], Optional[int]]]) -> None:
        # TODO: Delegate to persist.insert_resolved_relationship_mentions
        raise NotImplementedError

    def upsert_resolved_relationships_base(self, rows: List[Tuple[str, str, str, str, Optional[str], Optional[str]]]) -> int:
        # TODO: Delegate to persist.upsert_resolved_relationships_base
        raise NotImplementedError

