from __future__ import annotations

"""SQLite facade for persistence adapters (documents, KG, ER).

This class centralizes SQLite wiring so callers can construct one object
with a db_path and obtain typed repositories/stores implementing the
corresponding ports.
"""

from typing import Optional

from knowledge_graph.core.db.sql_lite.repository import SqlLiteRepository
from .document.document_repository import SQLiteDocumentRepository
from .knowledge_graph.graph_store import SQLiteGraphStore
from .entity_resolution.entity_resolution_store import SQLiteEntityResolutionStore


class SqlLite:
    def __init__(self, settings: Settings):
        # Underlying repository also ensures schema on init
        repo = SqlLiteRepository(settings.db_path)
        self._repo = repo
        self.db_path = repo.db_path

    # Schema management -------------------------------------------------
    def create_database(self) -> None:
        """Ensure database file exists and base tables are created."""
        # SqlLiteRepository.__init__ already creates tables; call again to be explicit
        try:
            self._repo._initialize_database()  # type: ignore[attr-defined]
        except Exception:
            # Fallback: instantiate a fresh repository to trigger initialization
            SqlLiteRepository(self.db_path)

    def create_tables(self) -> None:
        """Alias for create_database for semantic clarity."""
        self.create_database()

    def create_indexes(self) -> None:
        """No extra indexes beyond schema defaults for documents/KG currently."""
        # Index creation for knowledge bases lives in its repository.migrations.
        return None

    # Adapters ----------------------------------------------------------
    def document_repository(self) -> SQLiteDocumentRepository:
        return SQLiteDocumentRepository(self.db_path)

    def graph_store(self) -> SQLiteGraphStore:
        return SQLiteGraphStore(self.db_path)

    def entity_resolution_store(self) -> SQLiteEntityResolutionStore:
        return SQLiteEntityResolutionStore(self.db_path)
