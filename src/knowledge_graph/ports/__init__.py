"""Domain ports (interfaces) for persistence and graph access.

These interfaces define the contracts that outbound implementations (e.g.,
SQLite, Neo4j) must satisfy. Keep them free of concrete tech imports to
preserve portability and testability.
"""

from .knowledge_base import KnowledgeBaseRepository
from .document_repository import DocumentRepository
from .graph_store import GraphStore
from .entity_resolution_store import EntityResolutionStore

__all__ = [
    "KnowledgeBaseRepository",
    "DocumentRepository",
    "GraphStore",
    "EntityResolutionStore",
]

