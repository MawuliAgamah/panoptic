from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class GraphStore(ABC):
    """Port for persisting and querying knowledge graphs.

    Stores document-level entities/edges and builds graph snapshots. Queries
    may be scoped by knowledge base or document id.
    """

    @abstractmethod
    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any], *, kb_id: Optional[str] = None) -> bool:
        """Persist a document-level knowledge graph payload."""

    @abstractmethod
    def get_graph_snapshot(self, *, kb_id: Optional[str] = None, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a node/edge/documents snapshot filtered by kb and/or document."""

