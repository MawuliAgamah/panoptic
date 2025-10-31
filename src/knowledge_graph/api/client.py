from typing import Dict, Optional, Union, List, Any
import logging
from pathlib import Path
from datetime import datetime
from ..core.db.db_client import DatabaseClient
from ..pipeline import DocumentPipelineConfig
from ..config import (
    KnowledgeGraphConfig,
    DatabaseConfig,
    LLMConfig,
    CacheConfig,
    KGExtractionConfig,
    GraphDatabaseConfig,
    AuthCredentials
)


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
        """Configure unified logging for the application.

        - Sets a console handler on the root logger with a formatter that includes
          correlation fields injected by the InjectContextFilter.
        - Ensures base namespaces ("knowledge_graph", "knowledgeAgent") are set to the
          configured level and propagate to root so a single handler captures all logs.
        """
        from ..core.logging_utils import InjectContextFilter

        level = getattr(logging, log_level.upper(), logging.INFO)

        # Root logger configuration (single console handler)
        root_logger = logging.getLogger()
        root_logger.setLevel(level)

        # Avoid duplicate handlers
        if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
            handler = logging.StreamHandler()
            # Include correlation fields in the log format
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s | doc=%(doc_id)s run=%(run_id)s | %(message)s'
            )
            handler.setFormatter(formatter)
            handler.addFilter(InjectContextFilter())
            root_logger.addHandler(handler)

        # Ensure our primary namespaces propagate to root
        kg_logger = logging.getLogger("knowledge_graph")
        kg_logger.setLevel(level)
        kg_logger.propagate = True

        ka_logger = logging.getLogger("knowledgeAgent")
        ka_logger.setLevel(level)
        ka_logger.propagate = True

        # Client-specific logger for convenience
        self.logger = kg_logger
    
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
        from ..document.service import DocumentService
        from ..llm.service import LLMService
        from ..knowledge_graph.service import KnowledgeGraphService
        from ..llm.kg_extractor.service import KGExtractionService

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

        # Initialize knowledge graph and document services
        self.logger.info("Initializing knowledge graph service")
        self.knowledge_graph_service = KnowledgeGraphService(
            db_client=self.db_client,
            llm_service=self.llm_service,
            llm_provider=llm_provider
        )

        self.logger.info("Initializing document service")
        pipeline_settings = getattr(self.config, 'document_pipeline', None)
        pipeline_config = DocumentPipelineConfig(
            enable_enrichment=getattr(pipeline_settings, 'enable_enrichment', True),
            enable_kg_extraction=getattr(pipeline_settings, 'enable_kg_extraction', True),
            enable_persistence=getattr(pipeline_settings, 'enable_persistence', True),
            chunk_size=getattr(pipeline_settings, 'chunk_size', 1000),
            chunk_overlap=getattr(pipeline_settings, 'chunk_overlap', 200),
            chunker_type=getattr(pipeline_settings, 'chunker_type', 'structured_markdown'),
        )
        self.document_service = DocumentService(
            db_client=self.db_client,
            llm_service=self.llm_service,
            llm_provider=llm_provider,
            pipeline_config=pipeline_config,
            kg_service=self.knowledge_graph_service,
        )

    # Document Operations
    def add_document(self, document_path: str, document_id: str, document_type: Optional[str] = None, 
                    domain: Optional[str] = None, tags: Optional[List[str]] = None) -> str:
        """
        Add a document to the knowledge graph.
        
        Args:
            document_path: Path to the document file
            document_id: Unique identifier for the document
            document_type: Type of document (optional, will be inferred if not provided)
            domain: Domain/category for the document
            tags: List of tags for the document
            
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
            domain=domain,
            tags=tags,
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
    
    def extract_knowledge_graph_json(self, document_path: str, document_id: str, document_type: Optional[str] = None, 
                                     domain: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extract knowledge graph from a document and return as JSON data instead of saving to database.
        
        Args:
            document_path: Path to the document file
            document_id: Unique identifier for the document
            document_type: Type of document (optional)
            domain: Domain/category for the document
            tags: List of tags for the document
            
        Returns:
            Dictionary containing extracted entities, relationships, and metadata
        """
        self.logger.info(f"Extracting knowledge graph JSON from: {document_path}")
        
        try:
            pipeline_settings = getattr(self.config, 'document_pipeline', None)
            json_pipeline_config = DocumentPipelineConfig(
                enable_enrichment=getattr(pipeline_settings, 'enable_enrichment', True),
                enable_kg_extraction=getattr(pipeline_settings, 'enable_kg_extraction', True),
                enable_persistence=False,
                chunk_size=getattr(pipeline_settings, 'chunk_size', 1000),
                chunk_overlap=getattr(pipeline_settings, 'chunk_overlap', 200),
                chunker_type=getattr(pipeline_settings, 'chunker_type', 'structured_markdown'),
            )

            transient_pipeline = self.document_service.build_pipeline(json_pipeline_config)

            document = transient_pipeline.run(
                document_path=document_path,
                document_id=document_id,
                domain=domain,
                tags=tags,
            )
            if document is None:
                raise Exception(f"Failed to process document from {document_path}")
            
            # Convert to JSON format
            kg_json = {
                'entities': [],
                'relationships': [],
                'metadata': {
                    'document_id': document_id,
                    'title': document.title,
                    'file_path': document_path,
                    'file_type': getattr(document, 'file_type', ''),
                    'domain': domain,
                    'tags': tags or [],
                    'word_count': len(document.clean_content.split()) if document.clean_content else 0,
                    'processing_strategy': 'Document-level' if document.should_use_document_level_kg() else 'Chunk-level'
                }
            }
            
            # Extract entities
            if hasattr(document, 'knowledge_graph') and document.knowledge_graph:
                entities = document.knowledge_graph.get('entities', set())
                if isinstance(entities, set):
                    entities = list(entities)
                
                for entity in entities:
                    if isinstance(entity, str):
                        kg_json['entities'].append({
                            'name': entity,
                            'type': 'extracted',
                            'document_id': document_id,
                            'metadata': {
                                'domain': domain,
                                'tags': tags or []
                            }
                        })
                    elif isinstance(entity, dict):
                        entity_data = {
                            'name': entity.get('name', str(entity)),
                            'type': entity.get('type', 'extracted'),
                            'document_id': document_id,
                            'metadata': entity.get('metadata', {})
                        }
                        if domain:
                            entity_data['metadata']['domain'] = domain
                        if tags:
                            entity_data['metadata']['tags'] = tags
                        kg_json['entities'].append(entity_data)
                
                # Extract relationships
                relations = document.knowledge_graph.get('relations', [])
                for relation in relations:
                    if isinstance(relation, dict):
                        kg_json['relationships'].append({
                            'source_entity': relation.get('source', ''),
                            'target_entity': relation.get('target', ''),
                            'relation_type': relation.get('relation', relation.get('type', 'related_to')),
                            'document_id': document_id,
                            'metadata': relation.get('metadata', {})
                        })
                    elif isinstance(relation, (list, tuple)) and len(relation) >= 3:
                        kg_json['relationships'].append({
                            'source_entity': str(relation[0]),
                            'target_entity': str(relation[2]),
                            'relation_type': str(relation[1]),
                            'document_id': document_id,
                            'metadata': {}
                        })
            
            self.logger.info(f"Extracted KG JSON: {len(kg_json['entities'])} entities, {len(kg_json['relationships'])} relationships")
            return kg_json
            
        except Exception as e:
            self.logger.error(f"Error extracting knowledge graph JSON: {e}")
            # Return empty structure on error
            return {
                'entities': [],
                'relationships': [],
                'metadata': {
                    'document_id': document_id,
                    'error': str(e)
                }
            }


    
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

    
    def get_all_document_ids(self) -> List[str]:
        """
        Get all unique document IDs from entities.
        
        Returns:
            List of unique document IDs
        """
        snapshot = self.db_client.get_graph_snapshot()
        return [doc.get("id") for doc in snapshot.get("documents", [])]

    def get_graph_snapshot(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a GraphSnapshot derived from the SQLite persistence layer."""
        try:
            return self.db_client.get_graph_snapshot(document_id)
        except Exception as exc:
            self.logger.error(f"Failed to build graph snapshot: {exc}")
            return {"nodes": [], "edges": [], "documents": []}

    # Advanced KG Extraction using kggen
    def extract_knowledge_graph_with_kggen(self,text: str,context: Optional[str] = None,strategy: str = "detailed") -> Dict[str, Any]:
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

    # set up the client 
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

    
