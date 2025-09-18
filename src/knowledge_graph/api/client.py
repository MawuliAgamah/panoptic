from typing import Dict, Optional, Union, List, Any
import logging
from dataclasses import dataclass
from pathlib import Path
from src.knowledgeAgent.core.db.db_client import DatabaseClient




@dataclass
class GraphDatabaseConfig:
    db_type: str
    database: str
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    schema: Optional[str] = None
    pool_size: int = 5
    max_overflow: int = 10
    ssl_mode: Optional[str] = None
    application_name: Optional[str] = "KnowledgeAgent"

@dataclass
class AuthCredentials:
    username: str
    password: str
    auth_type: str = "basic"
    token: Optional[str] = None
    
class KnowledgeGraphClient:
    """
    Main client interface for interacting with Knowledge Graphs.
    Handles document processing, entity extraction, and graph operations.
    """
    
    def __init__(
        self,
        graph_db_config: Union[Dict, GraphDatabaseConfig],
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

        """

        self._configure_logging(log_level)
        
        # Initialize configuration
        self.cache_config = db_config
        self.db_config = db_config
        self.llm_config = llm_config
        self.cache_dir = self._setup_cache_directory(db_config)

        self.embedding_dimension = embedding_dimension
        self.max_connections = max_connections
        self.timeout = timeout
        
        # Initialize services (these would be separate classes)
        self.db_client = self._initialize_database_connection(db_config)
        self._initialize_services()
        
        self.logger.info("KnowledgeGraphClient initialized successfully")
    
    def _configure_logging(self, log_level: str) -> None:
        """Configure logging for the client."""
        self.logger = logging.getLogger("knowledgeAgent")
        level = getattr(logging, log_level.upper(), logging.INFO)
        self.logger.setLevel(level)
        # Add handlers, formatters, etc.
    
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
    
    
    def _initialize_database_connection(self,db_config):
        """Establish connection to the database."""
        if isinstance(db_config, dict) and "db_type" in db_config:
            self.logger.debug(f"Connecting to {db_config.get('db_type', 'unknown')} database")
            client = DatabaseClient(db_config)
        else:
            self.logger.error("Invalid database configuration")
            raise ValueError("Invalid database configuration")
        return client
    

    def _initialize_services(self) -> None:
        """Initialize all required services."""
        from src.knowledgeAgent.document.service import DocumentService
        from src.knowledgeAgent.llm.service import LLMService
        from src.knowledgeAgent.knowledge_graph.service import KnowledgeGraphService
        
        # Initialize LLM service with config
        self.llm_service = LLMService(config=self.llm_config)


        # Convert cache_config to format expected by DocumentService
        if isinstance(self.cache_config, str):
            doc_cache_config = {"enabled": True, "location": self.cache_dir}
        elif isinstance(self.cache_config, dict):
            doc_cache_config = self.cache_config
            if "enabled" not in doc_cache_config:
                doc_cache_config["enabled"] = True
            if "cache_location" in doc_cache_config:
                doc_cache_config["location"] = doc_cache_config["cache_location"]
        else:
            doc_cache_config = {"enabled": True, "location": self.cache_dir}
            
    
        # Initialize document service with LLM service
        self.logger.info(f"Initializing document service with cache config: {doc_cache_config}")
        self.document_service = DocumentService(db_client=self.db_client,llm_service=self.llm_service)
        self.logger.info(f"Initializing knowledge graph service with db config: {self.db_config}")
        self.knowledge_graph_service = KnowledgeGraphService(db_client=self.db_client,llm_service=self.llm_service)

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
    def query(self, query_text: str, graph_id: Optional[str] = None) -> List[Dict]:
        """
        Query the knowledge graph using natural language.
        
        Args:
            query_text: Natural language query
            graph_id: Optional graph ID (if not provided, uses default)
            
        Returns:
            results: List of matching results
        """
        # Implementation
        return [{"result": "not_implemented"}]
    
    # Connection Management
    def close(self) -> None:
        """Close all connections and free resources."""
        # Implementation to clean up connections
        self.logger.info("KnowledgeGraphClient closed")


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

