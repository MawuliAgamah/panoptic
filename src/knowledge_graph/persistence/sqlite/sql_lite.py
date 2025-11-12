from __future__ import annotations

"""SQLite facade for persistence adapters (documents, KG, ER).

This class centralizes SQLite wiring so callers can construct one object
with a db_path and obtain typed repositories/stores implementing the
corresponding ports.
"""

from typing import Optional

from ...core.db.sql_lite.repository import SqlLiteRepository
from .document.document_repository import SQLiteDocumentRepository
from .knowledge_graph.graph_store import SQLiteGraphStore
from .entity_resolution.entity_resolution_store import SQLiteEntityResolutionStore


class SqlLite:
    def __init__(self, settings: Settings):
        # Underlying repository also ensures schema on init
        repo = SqlLiteRepository(settings.db_path)
        self.db_path = repo.db_path

    # Schema management -------------------------------------------------
    def create_tables(self) -> None:
        """Ensure database file exists and base tables are created."""
        try:
           knowledge_base_repository.create_table()
           document_repository.create_table()
           tabular_document_repository.create_table()
           ontology_repository.create_table()
           
        except Exception as e:
            logger.error(f"Error creating tables: {e}")
            raise

    # Adapters ----------------------------------------------------------
    def document_repository(self) -> SQLiteDocumentRepository:
        return SQLiteDocumentRepository(self.db_path)
    
    def tabular_document_repository(self) -> SQLiteTabularDocumentRepository:
        return SQLiteTabularDocumentRepository(self.db_path)

    def graph_store(self) -> SQLiteGraphStore:
        return SQLiteGraphStore(self.db_path)

    def entity_resolution_store(self) -> SQLiteEntityResolutionStore:
        return SQLiteEntityResolutionStore(self.db_path)
