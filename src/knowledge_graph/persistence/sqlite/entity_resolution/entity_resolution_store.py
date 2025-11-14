from __future__ import annotations

"""SQLite implementation for EntityResolutionStore.

This adapter wraps the helper functions in entity_resolution.persist,
providing a simple adapter to work with direct database paths.
"""

from typing import Optional, List, Tuple, Any
import sqlite3
import logging
from pathlib import Path

from ....ports.entity_resolution_store import EntityResolutionRepository
from ....entity_resolution import persist as er_persist

logger = logging.getLogger(__name__)


class _DbAdapter:
    """Minimal adapter to provide what persist functions expect from DatabaseClient."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        # Create a mock sqlite_service with repository
        self.sqlite_service = type('obj', (object,), {
            'repository': type('obj', (object,), {'db_path': db_path})()
        })()


class SQLiteEntityResolutionRepository(EntityResolutionRepository):
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
        self._db_adapter = _DbAdapter(db_path)
    
    def _ensure_db_dir(self) -> None:
        """Ensure the database directory exists."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

    def create_tables(self) -> None:
        """Create tables - calls ensure_schema."""
        self.ensure_schema()

    def ensure_schema(self) -> None:
        """Ensure entity resolution schema exists."""
        try:
            er_persist.ensure_schema(self._db_adapter)
            logger.info("Entity resolution schema ensured")
        except Exception as e:
            logger.error(f"Error ensuring entity resolution schema: {e}")
            raise
    
    def fetch_mentions(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Any]:
        """Fetch entity mentions from the database."""
        try:
            return er_persist.fetch_mentions(self._db_adapter, doc_ids)
        except Exception as e:
            logger.error(f"Error fetching mentions: {e}")
            return []

    def fetch_relationships(self, *, kb_id: Optional[str] = None, doc_ids: Optional[List[str]] = None) -> List[Tuple]:
        """Fetch relationships from the database."""
        try:
            return er_persist.fetch_relationships(self._db_adapter, doc_ids)
        except Exception as e:
            logger.error(f"Error fetching relationships: {e}")
            return []

    def upsert_resolved_entities(self, items: List[Any]) -> int:
        """Upsert resolved entities."""
        try:
            return er_persist.upsert_resolved_entities(self._db_adapter, items)
        except Exception as e:
            logger.error(f"Error upserting resolved entities: {e}")
            return 0

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
        try:
            return er_persist.upsert_entity_resolution_map(self._db_adapter, normalized)  # type: ignore[arg-type]
        except Exception as e:
            logger.error(f"Error upserting entity resolution map: {e}")
            return 0

    def insert_resolved_relationship_mentions(self, rows: List[Tuple[str, str, str, Optional[int], Optional[str], Optional[int]]]) -> None:
        """Insert resolved relationship mentions."""
        try:
            er_persist.insert_resolved_relationship_mentions(self._db_adapter, rows)
        except Exception as e:
            logger.error(f"Error inserting resolved relationship mentions: {e}")
            raise

    def upsert_resolved_relationships_base(self, rows: List[Tuple[str, str, str, str, Optional[str], Optional[str]]]) -> int:
        """Upsert resolved relationships aggregate base rows."""
        try:
            er_persist.upsert_resolved_relationships_base(self._db_adapter, rows)
            # persist function does not return count; best-effort rows length
            return len(rows)
        except Exception as e:
            logger.error(f"Error upserting resolved relationships: {e}")
            return 0
