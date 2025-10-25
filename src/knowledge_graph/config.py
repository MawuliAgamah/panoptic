"""Configuration classes for Knowledge Graph system."""

from typing import Dict, Optional, Union, Any
from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv
load_dotenv()


@dataclass
class DatabaseConfig:
    """Database configuration for both graph DB and cache DB."""
    db_type: str
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    schema: Optional[str] = None
    db_location: Optional[str] = None  # For SQLite/JSON storage
    data_file: Optional[str] = None     # For JSON knowledge store
    pool_size: int = 5
    max_overflow: int = 10
    ssl_mode: Optional[str] = None
    application_name: Optional[str] = "KnowledgeGraph"


@dataclass
class LLMConfig:
    """LLM configuration with provider-specific settings."""
    provider: str = "openai"  # openai, ollama, etc.
    model: str = "gpt-3.5-turbo"
    api_key: Optional[str] = None
    temperature: float = 0.2
    max_tokens: int = 1000
    timeout: int = 30
    base_url: Optional[str] = None  # For custom endpoints

    def __post_init__(self):
        """Auto-populate API key from environment if not provided."""
        if self.provider == "openai" and not self.api_key:
            self.api_key = os.getenv("OPENAI_API_KEY")


@dataclass
class CacheConfig:
    """Cache configuration for document processing."""
    enabled: bool = True
    location: Optional[str] = None
    max_size_mb: int = 1000
    ttl_hours: int = 24

    def __post_init__(self):
        """Set default cache location if not provided."""
        if self.enabled and not self.location:
            import tempfile
            self.location = os.path.join(tempfile.gettempdir(), "knowledge_graph_cache")


@dataclass
class KGExtractionConfig:
    """Configuration for knowledge graph extraction."""
    strategy: str = "simple"  # simple, detailed
    use_clustering: bool = False
    chunk_size: int = 5000
    enable_kggen: bool = True
    fallback_to_mock: bool = True
    track_metadata: bool = True


@dataclass
class KnowledgeGraphConfig:
    """Main configuration class that consolidates all configs."""
    graph_db: DatabaseConfig
    cache_db: Optional[DatabaseConfig] = None
    llm: Optional[LLMConfig] = None
    cache: Optional[CacheConfig] = None
    kg_extraction: Optional[KGExtractionConfig] = None
    log_level: str = "INFO"
    max_connections: int = 10
    timeout: int = 30

    def __post_init__(self):
        """Set defaults for optional configurations."""
        if self.llm is None:
            self.llm = LLMConfig()

        if self.cache is None:
            self.cache = CacheConfig()

        if self.kg_extraction is None:
            self.kg_extraction = KGExtractionConfig()

        # Set cache DB to SQLite if not provided
        if self.cache_db is None:
            cache_dir = self.cache.location or os.path.join(os.getcwd(), "data")
            self.cache_db = DatabaseConfig(
                db_type="sqlite",
                db_location=os.path.join(cache_dir, "cache.db")
            )

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'KnowledgeGraphConfig':
        """Create configuration from dictionary."""
        # Extract graph_db config (required)
        graph_db_dict = config_dict.pop('graph_db', {})
        if not graph_db_dict:
            raise ValueError("graph_db configuration is required")
        graph_db = DatabaseConfig(**graph_db_dict)

        # Extract optional configs
        cache_db_dict = config_dict.pop('cache_db', None)
        cache_db = DatabaseConfig(**cache_db_dict) if cache_db_dict else None

        llm_dict = config_dict.pop('llm', {})
        llm = LLMConfig(**llm_dict) if llm_dict else None

        cache_dict = config_dict.pop('cache', {})
        cache = CacheConfig(**cache_dict) if cache_dict else None

        kg_extraction_dict = config_dict.pop('kg_extraction', {})
        kg_extraction = KGExtractionConfig(**kg_extraction_dict) if kg_extraction_dict else None

        return cls(
            graph_db=graph_db,
            cache_db=cache_db,
            llm=llm,
            cache=cache,
            kg_extraction=kg_extraction,
            **config_dict
        )

    @classmethod
    def create_default(cls, graph_db_config: Dict[str, Any]) -> 'KnowledgeGraphConfig':
        """Create default configuration with minimal graph DB config."""
        return cls(
            graph_db=DatabaseConfig(**graph_db_config),
            llm=LLMConfig(),
            cache=CacheConfig(),
            kg_extraction=KGExtractionConfig()
        )


# Legacy compatibility - keep old classes for backward compatibility
@dataclass
class GraphDatabaseConfig(DatabaseConfig):
    """Legacy alias for DatabaseConfig."""
    pass

@dataclass
class AuthCredentials:
    """Legacy authentication credentials class."""
    username: str
    password: str
    auth_type: str = "basic"
    token: Optional[str] = None