"""KnowledgeGraph - A module for creating and managing knowledge graphs with AI."""

from typing import Optional

__version__ = "0.1.0"

# Import main client and configuration classes
from .api.client import KnowledgeGraphClient
from .config import (
    KnowledgeGraphConfig,
    DatabaseConfig,
    LLMConfig,
    CacheConfig,
    KGExtractionConfig,
    # Legacy compatibility
    GraphDatabaseConfig,
    AuthCredentials
)
from .llm.kg_extractor.service import KGExtractionService

# Import core services (for advanced users)
from .document.service import DocumentService
from .llm.service import LLMService
from .knowledge_graph.service import KnowledgeGraphService
from .core.db.db_client import DatabaseClient

# Convenience functions
def create_client(
    graph_db_type: str = "json",
    data_file: Optional[str] = None,
    neo4j_uri: str = "bolt://localhost:7687",
    neo4j_user: str = "neo4j",
    neo4j_password: str = "password",
    openai_api_key: Optional[str] = None,
    *,
    kb_store_backend: Optional[str] = None,
    kb_store_location: Optional[str] = None,
) -> KnowledgeGraphClient:
    """
    Create a simple knowledge graph client with minimal configuration.

    Args:
        graph_db_type: Type of graph database ("json" or "neo4j")
        data_file: Path to JSON file (for json type), defaults to ./database/knowledge_store.json
        neo4j_uri: Neo4j database URI (for neo4j type)
        neo4j_user: Neo4j username (for neo4j type)
        neo4j_password: Neo4j password (for neo4j type)
        openai_api_key: OpenAI API key (will try to get from environment if not provided)

    Returns:
        Configured KnowledgeGraphClient ready to use
    """
    if graph_db_type == "json":
        return create_json_client(
            data_file=data_file,
            openai_api_key=openai_api_key,
            kb_store_backend=kb_store_backend,
            kb_store_location=kb_store_location,
        )
    else:
        return KnowledgeGraphClient.create_simple(
            neo4j_uri=neo4j_uri,
            neo4j_user=neo4j_user,
            neo4j_password=neo4j_password,
            openai_api_key=openai_api_key
        )

def create_json_client(
    data_file: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    *,
    kb_store_backend: Optional[str] = None,
    kb_store_location: Optional[str] = None,
) -> KnowledgeGraphClient:
    """
    Create a client using JSON for knowledge graph storage.

    Args:
        data_file: Path to JSON file for storing knowledge graph data
        openai_api_key: OpenAI API key

    Returns:
        Configured KnowledgeGraphClient with JSON storage
    """
    if data_file is None:
        import os
        # Default to database/knowledge_store.json
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(os.path.dirname(current_dir))
        data_file = os.path.join(project_root, "database", "knowledge_store.json")

    # Set up proper cache directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    cache_db_path = os.path.join(project_root, "database", "sql_lite", "knowledgebase.db")

    # Ensure cache directory exists
    os.makedirs(os.path.dirname(cache_db_path), exist_ok=True)
    
    sqlite_config = DatabaseConfig(
        db_type="sqlite",
        db_location=cache_db_path
    )

    # Dedicated KB database colocated with sqlite cache by default
    kb_db_path = os.path.join(project_root, "database", "sql_lite", "knowledgebase.db")
    kb_sqlite_config = DatabaseConfig(
        db_type="sqlite",
        db_location=kb_db_path
    )

    config = KnowledgeGraphConfig(
        graph_db=sqlite_config,
        cache_db=sqlite_config,
        kb_db=kb_sqlite_config,
        llm=LLMConfig(
            provider="openai",
            api_key=openai_api_key
        )
    )

    return KnowledgeGraphClient(
        config=config,
        kb_store_backend=kb_store_backend,
        kb_store_location=kb_store_location,
    )

__all__ = [
    # Main client
    "KnowledgeGraphClient",
    "create_client",
    "create_json_client",

    # Configuration classes
    "KnowledgeGraphConfig",
    "DatabaseConfig",
    "LLMConfig",
    "CacheConfig",
    "KGExtractionConfig",

    # Legacy compatibility
    "GraphDatabaseConfig",
    "AuthCredentials",

    # Services (for advanced users)
    "KGExtractionService",
    "DocumentService",
    "LLMService",
    "KnowledgeGraphService",
    "DatabaseClient"
]
