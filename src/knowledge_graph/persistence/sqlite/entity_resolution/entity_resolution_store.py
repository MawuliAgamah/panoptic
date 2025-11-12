from __future__ import annotations

"""SQLite implementation scaffold for EntityResolutionStore.

This adapter will wrap the helper functions in entity_resolution.persist,
adding kb_id filtering once the schema supports it. For now, it exposes
method stubs with the correct signatures.
"""

from typing import Optional, List, Tuple, Any
from ....ports.entity_resolution_store import EntityResolutionStore
from ....core.db.db_client import DatabaseClient
from ....entity_resolution import persist as er_persist


class SQLiteEntityResolutionStore(EntityResolutionStore):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _db(self) -> DatabaseClient:
        return DatabaseClient(graph_db_config=None, cache_db_config={"db_type": "sqlite", "db_location": self.db_path})

    def ensure_schema(self) -> None:
        db = self._db()
        try:
            er_persist.ensure_schema(db)
        finally:
            db.close()

    def fetch_mentions(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Any]:
        db = self._db()
        try:
            return er_persist.fetch_mentions(db, doc_ids)
        finally:
            db.close()

    def fetch_relationships(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Tuple]:
        db = self._db()
        try:
            return er_persist.fetch_relationships(db, doc_ids)
        finally:
            db.close()

    def upsert_resolved_entities(self, items: List[Any]) -> int:
        db = self._db()
        try:
            return er_persist.upsert_resolved_entities(db, items)
        finally:
            db.close()

    def upsert_entity_resolution_map(self, mappings: List[Tuple[str, str, str, str, float]]) -> int:
        """Accepts flexible tuple lengths; normalizes for persist function.

        Supported tuple forms:
          - (entity_id, resolved_id, normalized_key, document_id, strategy, confidence)
          - (entity_id, resolved_id, normalized_key, strategy, confidence)  -> document_id=None
          - (entity_id, resolved_id, normalized_key, document_id)           -> strategy='exact', confidence=1.0
        """
        normalized: List[Tuple[str, str, str, Optional[str], str, float]] = []
        for tup in mappings or []:
            if len(tup) == 6:
                e, r, k, d, s, c = tup  # type: ignore[misc]
                normalized.append((e, r, k, d, s, float(c)))
            elif len(tup) == 5:
                e, r, k, s, c = tup  # type: ignore[misc]
                normalized.append((e, r, k, None, s, float(c)))
            elif len(tup) == 4:
                e, r, k, d = tup  # type: ignore[misc]
                normalized.append((e, r, k, d, "exact", 1.0))
            else:
                raise ValueError("Invalid mapping tuple length")
        db = self._db()
        try:
            return er_persist.upsert_entity_resolution_map(db, normalized)  # type: ignore[arg-type]
        finally:
            db.close()

    def insert_resolved_relationship_mentions(self, rows: List[Tuple[str, str, str, Optional[int], Optional[str], Optional[int]]]) -> None:
        db = self._db()
        try:
            er_persist.insert_resolved_relationship_mentions(db, rows)
        finally:
            db.close()

    def upsert_resolved_relationships_base(self, rows: List[Tuple[str, str, str, str, Optional[str], Optional[str]]]) -> int:
        db = self._db()
        try:
            er_persist.upsert_resolved_relationships_base(db, rows)
            # persist function does not return count; best-effort rows length
            return len(rows)
        finally:
            db.close()
