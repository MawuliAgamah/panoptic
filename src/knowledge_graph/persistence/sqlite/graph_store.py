from __future__ import annotations

"""SQLite implementation scaffold for GraphStore.

This adapter will use the existing SQLLiteService/SqlLiteRepository to persist
knowledge graphs and build snapshots. For now it provides method stubs.
"""

from typing import Optional, Dict, Any
from knowledge_graph.ports.graph_store import GraphStore


class SQLiteGraphStore(GraphStore):
    def __init__(self, db_path: str):
        self.db_path = db_path

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any], *, kb_id: Optional[str] = None) -> bool:
        # TODO: Delegate to SqlLiteRepository.save_knowledge_graph with kb_id support once added
        raise NotImplementedError

    def get_graph_snapshot(self, *, kb_id: Optional[str] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
        # TODO: Delegate to SqlLiteRepository.get_graph_snapshot with kb_id filtering once added
        raise NotImplementedError

