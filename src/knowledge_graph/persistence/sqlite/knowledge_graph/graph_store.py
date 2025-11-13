from __future__ import annotations

"""SQLite implementation scaffold for GraphStore.

This adapter will use the existing SQLLiteService/SqlLiteRepository to persist
knowledge graphs and build snapshots. For now it provides method stubs.
"""

from typing import Optional, Dict, Any
from ....ports.graph_repository import GraphRepository
from ....core.db.sql_lite.repository import SqlLiteRepository


class SQLiteGraphRepository(GraphRepository):
    """SQLite implementation of GraphStore port."""
    
    def __init__(self, db_path: str, shared_repo=None):
        # Use shared repository if provided, otherwise create new one
        if shared_repo:
            self._repo = shared_repo
        else:
            self._repo = SqlLiteRepository(db_path)
        self.db_path = self._repo.db_path

    def create_tables(self) -> bool:
        """Ensure tables are initialized."""
        self._repo._ensure_initialized()
        return True

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any], *, kb_id: Optional[str] = None) -> bool:
        """Persist a document-level knowledge graph payload."""
        # kb_id is unused in current schema
        return self._repo.save_knowledge_graph(document_id, kg_data)

    def get_graph_snapshot(self, *, kb_id: Optional[str] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a node/edge/documents snapshot filtered by kb and/or document."""
        # kb_id filtering not supported yet
        return self._repo.get_graph_snapshot(document_id)
