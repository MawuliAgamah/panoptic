from __future__ import annotations

"""SQLite implementation scaffold for GraphStore.

This adapter will use the existing SQLLiteService/SqlLiteRepository to persist
knowledge graphs and build snapshots. For now it provides method stubs.
"""

from typing import Optional, Dict, Any
from knowledge_graph.ports.graph_repository import GraphStore
from knowledge_graph.core.db.sql_lite.repository import SqlLiteRepository


class SQLiteGraphStore(GraphStore):
    def __init__(self, db_path: str):
        self._repo = SqlLiteRepository(db_path)
        self.db_path = self._repo.db_path

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any], *, kb_id: Optional[str] = None) -> bool:
        # kb_id is unused in current schema
        return self._repo.save_knowledge_graph(document_id, kg_data)

    def get_graph_snapshot(self, *, kb_id: Optional[str] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
        # kb_id filtering not supported yet
        return self._repo.get_graph_snapshot(document_id)
