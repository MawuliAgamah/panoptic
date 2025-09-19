from typing import Dict, Optional, Union, List, Any
import logging
from pathlib import Path
from knowledge_graph.core.db.db_client import DatabaseClient
from knowledge_graph.config import (
    KnowledgeGraphConfig,
    DatabaseConfig,
    LLMConfig,
    CacheConfig,
    KGExtractionConfig,
    # Legacy imports for backward compatibility
    GraphDatabaseConfig,
    AuthCredentials
)




# Legacy config classes are now imported from config.py
# This keeps backward compatibility while centralizing configuration
    
class KnowledgeGraphClient:
    """
    Main client interface for interacting with Knowledge Graphs.
    Handles document processing, entity extraction, and graph operations.

    Supports both new unified configuration and legacy configuration for backward compatibility.
    Integrates with kggen for advanced knowledge graph extraction.
    """
    
    def __init__(
        self,
        config: Optional[Union[KnowledgeGraphConfig, Dict]] = None,
        # Legacy parameters for backward compatibility
        graph_db_config: Optional[Union[Dict, GraphDatabaseConfig]] = None,
        auth_credentials: Optional[Union[Dict, AuthCredentials]] = None,
        db_config: Optional[Union[Dict, str]] = None,
        log_level: str = "INFO",
        llm_config: Optional[Dict] = None,
        models: Optional[Dict[str, str]] = None,
        embedding_dimension: int = 768,
        max_connections: int = 10,
        timeout: int = 30
    ):
        """
        Initialize the Knowledge Graph Client.

        Args:
            config: New KnowledgeGraphConfig object or dict
            graph_db_config: Legacy graph database config (for backward compatibility)
            db_config: Legacy cache database config (for backward compatibility)
            llm_config: Legacy LLM config (for backward compatibility)
            log_level: Logging level
            **kwargs: Additional legacy parameters
        """

        # Handle configuration - support both new and legacy approaches
        if config is not None:
            # New configuration approach
            if isinstance(config, dict):
                self.config = KnowledgeGraphConfig.from_dict(config)
            else:
                self.config = config
        else:
            # Legacy configuration approach - build new config from old parameters
            if not graph_db_config:
                raise ValueError("Either 'config' or 'graph_db_config' must be provided")

            # Convert legacy config to new format
            legacy_config = {
                'graph_db': graph_db_config if isinstance(graph_db_config, dict) else graph_db_config.__dict__,
                'log_level': log_level,
                'max_connections': max_connections,
                'timeout': timeout
            }

            if db_config:
                if isinstance(db_config, str):
                    legacy_config['cache_db'] = {'db_type': 'sqlite', 'db_location': db_config}
                else:
                    legacy_config['cache_db'] = db_config

            if llm_config:
                legacy_config['llm'] = llm_config

            self.config = KnowledgeGraphConfig.from_dict(legacy_config)

        self._configure_logging(self.config.log_level)

        # Initialize services
        self.db_client = self._initialize_database_connection()
        self._initialize_services()

        self.logger.info("KnowledgeGraphClient initialized successfully")
    
    def _configure_logging(self, log_level: str) -> None:
        """Configure logging for the client."""
        self.logger = logging.getLogger("knowledge_graph")
        level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        # Add console handler if not already present
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
    
    def _setup_cache_directory(self, cache_config: Optional[Union[Dict, str]]) -> str:
        """Set up and validate the cache directory."""
        import os
        import tempfile
        
        # If cache_config is a string, use it as directory path
        if isinstance(cache_config, str):
            if os.path.exists(cache_config):
                return cache_config
            else:
                try:
                    os.makedirs(cache_config, exist_ok=True)
                    return cache_config
                except Exception as e:
                    self.logger.warning(f"Failed to create cache directory {cache_config}: {e}")
                    
        # If cache_config is a dict, extract location
        elif isinstance(cache_config, dict) and "cache_location" in cache_config:
            location = cache_config["cache_location"]
            if os.path.exists(os.path.dirname(location)):
                return os.path.dirname(location)
        
        # Default to system temp directory
        default_dir = os.path.join(tempfile.gettempdir(), "knowledgeAgent_cache")
        os.makedirs(default_dir, exist_ok=True)
        self.logger.info(f"Using default cache directory: {default_dir}")
        return default_dir
    
    
    def _initialize_database_connection(self):
        """Establish connection to both cache and graph databases."""
        # Prepare configurations for DatabaseClient
        graph_db_config = self.config.graph_db.__dict__
        cache_db_config = self.config.cache_db.__dict__ if self.config.cache_db else None

        self.logger.debug(f"Initializing graph DB: {graph_db_config.get('db_type', 'unknown')}")
        if cache_db_config:
            self.logger.debug(f"Initializing cache DB: {cache_db_config.get('db_type', 'unknown')}")

        try:
            # Pass both configs to DatabaseClient - it will handle the separation
            client = DatabaseClient(
                graph_db_config=graph_db_config,
                cache_db_config=cache_db_config
            )
            return client
        except Exception as e:
            self.logger.error(f"Failed to initialize database connection: {e}")
            raise ValueError(f"Invalid database configuration: {e}")
    

    def _initialize_services(self) -> None:
        """Initialize all required services."""
        from knowledge_graph.document.service import DocumentService
        from knowledge_graph.llm.service import LLMService
        from knowledge_graph.knowledge_graph.service import KnowledgeGraphService
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        # Initialize LLM service with new config structure
        llm_config_dict = self.config.llm.__dict__ if self.config.llm else {}
        self.llm_service = LLMService(config=llm_config_dict)

        # Initialize KG extraction service with kggen integration
        kg_extraction_config = self.config.kg_extraction.__dict__ if self.config.kg_extraction else {}
        llm_provider = self.config.llm.provider if self.config.llm else "openai"

        self.kg_extraction_service = KGExtractionService(
            llm_provider=llm_provider,
            **{**llm_config_dict, **kg_extraction_config}
        )

        # Initialize document and knowledge graph services
        self.logger.info("Initializing document service")
        self.document_service = DocumentService(
            db_client=self.db_client,
            llm_service=self.llm_service,
            llm_provider=llm_provider
        )

        self.logger.info("Initializing knowledge graph service")
        self.knowledge_graph_service = KnowledgeGraphService(
            db_client=self.db_client,
            llm_service=self.llm_service,
            llm_provider=llm_provider
        )

    # Document Operations
    def add_document(self, document_path: str,document_id: str,document_type: Optional[str] = None) -> str:
        """
        Add a document to the knowledge graph.
        
        Args:
            document_path: Path to the document file
            document_type: Type of document (optional, will be inferred if not provided)
            
        Returns:
            document_id: Unique ID for the added document
        """
        self.logger.info(f"Adding document: {document_path}")
        
        # Infer document type if not provided
        if document_type is None:
            # Simple inference based on file extension
            import os
            ext = os.path.splitext(document_path)[1].lower()
            if ext == '.pdf':
                document_type = 'pdf'
            elif ext in ['.doc', '.docx']:
                document_type = 'docx'
            elif ext in ['.md', '.markdown']:
                document_type = 'markdown'
            elif ext in ['.txt']:
                document_type = 'text'
            else:
                document_type = 'unknown'
            
            self.logger.info(f"Inferred document_type: {document_type}")
        
        # If document_id is None, generate a fallback ID
        if document_id is None:
            import hashlib
            import time
            fallback_id = hashlib.md5(f"{document_path}:{time.time()}".encode()).hexdigest()
            self.logger.warning(f"Document service returned None ID, using fallback: {fallback_id}")
            document_id = fallback_id
        
        # Use document service to process the document
        result_id = self.document_service.add_document(
            document_path=document_path, 
            document_type=document_type,
            document_id=document_id,
            cache=True
            )
        document_id = result_id if result_id is not None else document_id
            
        self.logger.info(f"Document added with ID: {document_id}")
        return document_id
    
    def delete_document(self,document_id: str):
        self.document_service.delete_document(document_id)
        self.logger.info(f"Document deleted with ID: {document_id}")

    def get_cached_document(self,document_id):
        document_object = self.db_client.get_document(document_id=document_id)
        return document_object
    
    def extract_document_ontology(self, document_id: str):
        """
        Process a document to extract entities and relationships.
        
        Args:
            document_id: ID of the document to process
            
        Returns:
            processing_results: Dictionary with processing statistics
        """
        self.knowledge_graph_service.agentic_ontology_extraction(document_id)
        self.logger.info(f"Ontology extracted for document {document_id}")

    
    # Graph Operations
    def create_graph(self, name: str, description: Optional[str] = None) -> str:
        """
        Create a new knowledge graph.
        
        Args:
            name: Name for the new graph
            description: Optional description
            
        Returns:
            graph_id: Unique ID for the created graph
        """
        # Implementation
        return f"graph_{name}"
    
    # Query Operations
    def query(self, query_text: str, graph_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Query the knowledge graph using natural language.

        Args:
            query_text: Natural language query
            graph_id: Optional graph ID (if not provided, uses default)

        Returns:
            Dictionary with query results including entities and relationships
        """
        return self.db_client.query_knowledge_graph(query_text)

    def get_knowledge_graph_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the knowledge graph.

        Returns:
            Dictionary with statistics about entities, relationships, etc.
        """
        return self.db_client.get_graph_stats()

    def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for entities in the knowledge graph.

        Args:
            query: Search query

        Returns:
            List of matching entities
        """
        if self.db_client.json_kg_service:
            return self.db_client.json_kg_service.search_entities(query)
        else:
            self.logger.warning("Entity search not available for current database configuration")
            return []

    def search_relationships(self, query: str) -> List[Dict[str, Any]]:
        """
        Search for relationships in the knowledge graph.

        Args:
            query: Search query

        Returns:
            List of matching relationships
        """
        if self.db_client.json_kg_service:
            return self.db_client.json_kg_service.search_relationships(query)
        else:
            self.logger.warning("Relationship search not available for current database configuration")
            return []

    def get_entity_relationships(self, entity_name: str) -> List[Dict[str, Any]]:
        """
        Get all relationships for a specific entity.

        Args:
            entity_name: Name of the entity

        Returns:
            List of relationships involving the entity
        """
        if self.db_client.json_kg_service:
            return self.db_client.json_kg_service.get_entity_relationships(entity_name)
        else:
            self.logger.warning("Entity relationship lookup not available for current database configuration")
            return []
    
    # Advanced KG Extraction using kggen
    def extract_knowledge_graph_advanced(
        self,
        text: str,
        context: Optional[str] = None,
        strategy: str = "detailed"
    ) -> Dict[str, Any]:
        """
        Extract knowledge graph using advanced kggen integration.

        Args:
            text: Input text to extract from
            context: Optional context for better extraction
            strategy: Extraction strategy ("simple", "detailed")

        Returns:
            Dictionary with entities, relations, and metadata
        """
        return self.kg_extraction_service.extract_from_text(
            text=text,
            context=context,
            strategy=strategy,
            track_metadata=True
        )

    # Connection Management and Context Manager Support
    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()

    def close(self) -> None:
        """Close all connections and free resources."""
        if hasattr(self.db_client, 'close'):
            self.db_client.close()
        self.logger.info("KnowledgeGraphClient closed")

    # Class methods for easy client creation
    @classmethod
    def create_default(
        cls,
        graph_db_config: Dict[str, Any],
        llm_provider: str = "openai",
        api_key: Optional[str] = None
    ) -> 'KnowledgeGraphClient':
        """
        Create a client with default configuration.

        Args:
            graph_db_config: Graph database configuration
            llm_provider: LLM provider ("openai", "ollama")
            api_key: API key for the LLM provider

        Returns:
            Configured KnowledgeGraphClient instance
        """
        config = KnowledgeGraphConfig.create_default(graph_db_config)
        if llm_provider:
            config.llm.provider = llm_provider
        if api_key:
            config.llm.api_key = api_key

        return cls(config=config)

    @classmethod
    def from_config_file(cls, config_path: Union[str, Path]) -> 'KnowledgeGraphClient':
        """
        Create a client from a configuration file.

        Args:
            config_path: Path to YAML or JSON configuration file

        Returns:
            Configured KnowledgeGraphClient instance
        """
        import yaml
        import json

        config_path = Path(config_path)

        with open(config_path, 'r') as f:
            if config_path.suffix.lower() in ['.yaml', '.yml']:
                config_dict = yaml.safe_load(f)
            else:
                config_dict = json.load(f)

        config = KnowledgeGraphConfig.from_dict(config_dict)
        return cls(config=config)

    @classmethod
    def create_simple(
        cls,
        neo4j_uri: str = "bolt://localhost:7687",
        neo4j_user: str = "neo4j",
        neo4j_password: str = "password",
        openai_api_key: Optional[str] = None
    ) -> 'KnowledgeGraphClient':
        """
        Create a simple client with minimal configuration.

        Args:
            neo4j_uri: Neo4j connection URI
            neo4j_user: Neo4j username
            neo4j_password: Neo4j password
            openai_api_key: OpenAI API key

        Returns:
            Configured KnowledgeGraphClient instance
        """
        graph_db_config = {
            "db_type": "neo4j",
            "host": neo4j_uri.split("://")[1].split(":")[0],
            "port": int(neo4j_uri.split(":")[-1]),
            "username": neo4j_user,
            "password": neo4j_password,
            "database": "neo4j"
        }

        return cls.create_default(
            graph_db_config=graph_db_config,
            llm_provider="openai",
            api_key=openai_api_key
        )


if __name__ == "__main__":
    import os
    from pathlib import Path
    import dotenv
    
    # Find the project root directory (where .env file is located)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    dotenv.load_dotenv(project_root / ".env")    

    # Get API key from environment
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable is not set")

    client = KnowledgeGraphClient(
        graph_db_config={
            "db_type": "neo4j",
            "host": "localhost",
            "port": 7687,
            "database": "knowledge",
            "username": "neo4j",
            "password": "password"
        },
        db_config={
            "db_type": "sqlite",
            "db_location": "./data/cache.db"  # Use relative path
        },
        llm_config={
            "model": "gpt-3.5-turbo",
            "temperature": 0.2,
            "api_key": api_key
        })

    # client.delete_document(document_id="2")

    # client.add_document(
    #          document_path="./sample_documents/sample.md",
    #          document_type="markdown",
    #          document_id="2"
    #          )
    
    #client.get_cached_document(document_id="1234567890")
    client.extract_document_ontology(document_id="2")
    
    # document.display()
    client.close()

