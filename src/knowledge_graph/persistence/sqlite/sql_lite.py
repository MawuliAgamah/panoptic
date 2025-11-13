from __future__ import annotations

"""SQLite facade for persistence adapters (documents, KG, ER).

This class centralizes SQLite wiring so callers can construct one object
with a db_path and obtain typed repositories/stores implementing the
corresponding ports.
"""

from typing import Optional
import logging
import os
from pathlib import Path

from .document.document_repository import SQLiteDocumentRepository
from .document.tabular.tabular_doc_repository import SQLiteTabularDocumentRepository
from .knowledge_graph.graph_store import SQLiteGraphRepository
from .entity_resolution.entity_resolution_store import SQLiteEntityResolutionRepository
from .knowledge_graph.knowledge_base_repository import SQLiteKnowledgeBaseRepository
from ...settings.settings import Settings

logger = logging.getLogger(__name__)


class SqlLite:
    """SQLite persistence facade providing access to all repositories and stores."""
    
    def __init__(self, settings: Settings):
        """Initialize SqlLite facade with database path from settings.
        
        Args:
            settings: Settings object containing database configuration
        """
        self.db_path = settings.db.db_location
        
        # Create a single shared SqlLiteRepository instance
        from ...core.db.sql_lite.repository import SqlLiteRepository
        self._shared_repo = SqlLiteRepository(self.db_path)

    # Create all database tables if they don't exist -------------------------------------------------
    def create_tables(self) -> None:
        """Ensure database file exists and base tables are created."""
        try:
            # Initialize the shared repository (lazy, so this triggers initialization)
            self._shared_repo._ensure_initialized()
            
            # Create other repositories (they'll share the same repo instance)
            document_repository = SQLiteDocumentRepository(self.db_path, shared_repo=self._shared_repo)
            knowledge_base_repository = SQLiteKnowledgeBaseRepository(self.db_path)
            graph_repository = SQLiteGraphRepository(self.db_path, shared_repo=self._shared_repo)
            entity_resolution_repository = SQLiteEntityResolutionRepository(self.db_path)
            
            # These are mostly no-ops now since tables are initialized lazily
            document_repository.create_tables()
            knowledge_base_repository.create_tables()
            graph_repository.create_tables()
            entity_resolution_repository.ensure_schema()
        except Exception as e:
            logger.error("Error creating tables: %s", e)
            raise

    # Adapters ----------------------------------------------------------
    def document_repository(self) -> SQLiteDocumentRepository:
        return SQLiteDocumentRepository(self.db_path, shared_repo=self._shared_repo)
    
    def tabular_document_repository(self) -> SQLiteTabularDocumentRepository:
        return SQLiteTabularDocumentRepository(self.db_path)
    
    def graph_repository(self) -> SQLiteGraphRepository:
        return SQLiteGraphRepository(self.db_path, shared_repo=self._shared_repo)

    def entity_resolution_repository(self) -> SQLiteEntityResolutionRepository:
        return SQLiteEntityResolutionRepository(self.db_path)

    def knowledge_base_repository(self) -> SQLiteKnowledgeBaseRepository:
        return SQLiteKnowledgeBaseRepository(self.db_path)
