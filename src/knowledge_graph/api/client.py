from typing import Dict, Optional, Union, List, Any, Tuple
import uuid as _uuid
import logging
from pathlib import Path
from datetime import datetime
from ..document_ingestion import DocumentPipeline # , DocumentPipelineConfig, DocumentPipelineServices
from ..document_ingestion.factory import PipelineFactory
from ..config import (
    KnowledgeGraphConfig,
    DatabaseConfig,
    LLMConfig,
    CacheConfig,
    KGExtractionConfig,
    GraphDatabaseConfig,
    AuthCredentials
)
from ..data_structs.knowledge_base import KnowledgeBase

from ..persistence.json.knowledge_base_repository import JSONKnowledgeBaseRepository
from ..persistence.sqlite.knowledge_graph.knowledge_base_repository import (
    SQLiteKnowledgeBaseRepository,
)
import json as _json
import re as _re
import os as _os
from ..settings.settings import Settings
import logging
logger = logging.getLogger(__name__)

class KnowledgeGraphClient:
    """
    Main client interface for interacting with Knowledge Graphs.
    """
    
    def __init__(
        self,
        settings
    ):
        """Initialize the Knowledge Graph Client.

        """
        # Store settings first so it's available for _initialise_db()
        self.settings = settings
        # self._configure_logging(self.config.log_level)
        self._initialize_services()
        self._initialise_db()
        self.kb_repo = self.sql_lite.knowledge_base_repository()
            
    def _initialise_db(self):
        from ..persistence.sqlite.sql_lite import SqlLite
        self.sql_lite = SqlLite(self.settings)
        self.sql_lite.create_tables()
        
        
        
    
    def _initialize_services(self) -> None:
        """Initialize all required services."""
        from ..llm.service import LLMService
        from ..knowledge_graph.service import KnowledgeGraphService
        from ..llm.kg_extractor.service import KGExtractionService

        # Initialize LLM service with new config structure
        # llm_config_dict = self.config.llm.__dict__ if self.config.llm else {}
        # self.llm_service = LLMService(config=llm_config_dict)

        # Initialize KG extraction service with kggen integration
        # kg_extraction_config = self.config.kg_extraction.__dict__ if self.config.kg_extraction else {}
        # llm_provider = self.config.llm.provider if self.config.llm else "openai"

        # self.kg_extraction_service = KGExtractionService(
        #     llm_provider=llm_provider,
        #     **{**llm_config_dict, **kg_extraction_config}
        # ) 

        # Initialize knowledge graph and document services
        logger.info("Initializing knowledge graph service")
        # self.knowledge_graph_service = KnowledgeGraphService(
        #     db_client=self.db_client,
        #     llm_service=self.llm_service,
        #     llm_provider=llm_provider,
        #     kg_extraction_config=kg_extraction_config
        # )

        # Prepare pipeline configuration (used by factory-built pipelines)
        # pipeline_settings = getattr(self.config, 'document_pipeline', None)
        # self.pipeline_config = DocumentPipelineConfig(
        #     enable_enrichment=getattr(pipeline_settings, 'enable_enrichment', True),
        #     enable_kg_extraction=getattr(pipeline_settings, 'enable_kg_extraction', True),
        #     enable_persistence=getattr(pipeline_settings, 'enable_persistence', True),
        #     chunk_size=getattr(pipeline_settings, 'chunk_size', 1000),
        #     chunk_overlap=getattr(pipeline_settings, 'chunk_overlap', 200),
        #     chunker_type=getattr(pipeline_settings, 'chunker_type', 'auto'),
        # )
        # Keep llm_provider for pipeline services construction
        # self.llm_provider = llm_provider

    # Document Operations
    def add_document(self, document_path: str,kb_id: str) -> str:
        """Add a document to the knowledge graph using the appropriate pipeline.

        Auto-generates a document ID and routes to a CSV or general pipeline
        based on file extension.

        Returns the generated document ID.
        """
        logger.info(f"Adding document: {document_path}")
        document_id = f"doc_{_uuid.uuid4().hex[:8]}"
        pipeline = PipelineFactory.for_file(document_path)
        
        document = pipeline.run(
            document_path=document_path,
            document_id=document_id,
            kb_id=kb_id,
        )            
        logger.info(f"Document added with ID: {document_id}")
        return document_id

    def upload_file(self, file_path: str, kb_id: str) -> str:
        """Convenience: upload/ingest a file and route to the appropriate pipeline.

        Auto-generates a document ID and returns it.
        """
        return self.add_document(document_path=file_path, kb_id=kb_id)
    
    def delete_document(self,document_id: str):
        try:
            self.sql_lite.document_repository().delete_document(document_id)
        except Exception:
            self.logger.exception("Failed to delete document %s", document_id)
        self.logger.info(f"Document deleted with ID: {document_id}")

    # -------------------------------------------------------------- 
    # Knowledge Base operations (JSON-backed registry)
    # --------------------------------------------------------------

    class KnowledgeBaseHandle:
        """A lightweight handle bound to a specific knowledge base.

        Exposes KB-scoped operations (e.g., upload_file) in future iterations.
        """

        def __init__(self, client: "KnowledgeGraphClient", kb: KnowledgeBase):
            self._client = client
            self.id = kb.id
            self.name = kb.name
            self.slug = kb.slug
            self.owner_id = kb.owner_id

        def __repr__(self) -> str:  # pragma: no cover
            return f"KnowledgeBaseHandle(id={self.id!r}, name={self.name!r}, owner_id={self.owner_id!r})"

    def create_knowledgebase(self, name: str, owner_id: Optional[str] = None, description: Optional[str] = None) -> "KnowledgeBaseHandle":
        """Create (or return existing) knowledge base for an owner.

        Idempotent on (owner_id, slug). Returns a handle bound to the KB.
        """
        slug = self._slugify(name)
        logger.info("KB create", extra={"kb_name": name, "kb_slug": slug, "owner_id": owner_id or "-"})
        kb = self.kb_repo.create(name=name, slug=slug, owner_id=owner_id, description=description)
        logger.info("KB create done", extra={"kb_id": kb.id, "kb_slug": kb.slug, "owner_id": kb.owner_id or "-"})
        return self.KnowledgeBaseHandle(self, kb)   

    def get_knowledgebase(self, id_or_name: str, owner_id: Optional[str] = None) -> "KnowledgeBaseHandle":
        """Lookup a knowledge base by id, slug, or exact name.

        If owner_id is provided, it scopes the match; otherwise first match is returned.
        Raises ValueError if not found.
        """
        logger.info("KB get", extra={"lookup": id_or_name, "owner_id": owner_id or "-"})
        # id
        kb = self.kb_repo.get_by_id(id_or_name)
        if kb and (owner_id is None or kb.owner_id == owner_id):
            return self.KnowledgeBaseHandle(self, kb)
        # slug
        slug = self._slugify(id_or_name)
        kb = self.kb_repo.get_by_slug(slug, owner_id=owner_id)
        if kb:
            return self.KnowledgeBaseHandle(self, kb)
        # name match: list and match exact
        all_kb = self.kb_repo.list(owner_id=owner_id)
        for it in all_kb:
            if it.name == id_or_name:
                return self.KnowledgeBaseHandle(self, it)
        raise ValueError(f"Knowledge base not found: {id_or_name}")

    def list_knowledgebases(self, owner_id: Optional[str] = None) -> List[KnowledgeBase]:
        """List all knowledge bases, optionally filtered by owner."""
        items = self.kb_repo.list(owner_id=owner_id)
        logger.info("KB list", extra={"owner_id": owner_id or "-", "kb_count": len(items)})
        return items

    # ---- Internal KB registry helpers ----
    def _resolve_kb_registry_path(self) -> str:
        """Compute a stable path for the KB registry JSON file."""
        try:
            # Place under project_root/database/knowledge_bases.json
            project_root = Path(__file__).resolve().parents[3]
            registry = project_root / "database" / "knowledge_bases.json"
            return str(registry)
        except Exception:
            # Fallback to current working directory
            return str(Path.cwd() / "knowledge_bases.json")

    def _default_sqlite_db_path(self) -> str:
        """Default SQLite DB file for knowledge base store if none provided."""
        try:
            project_root = Path(__file__).resolve().parents[3]
            return str(project_root / "database" / "sql_lite" / "document_db.db")
        except Exception:
            return str(Path.cwd() / "document_db.db")

    def _resolve_kb_sqlite_path_override(self, override: Optional[str]) -> Optional[str]:
        if not override:
            return None
        try:
            p = Path(override)
            if not p.is_absolute():
                # Resolve relative to project root if possible
                project_root = Path(__file__).resolve().parents[3]
                p = (project_root / p).resolve()
            return str(p)
        except Exception:
            return override

    @staticmethod
    def _ensure_parent_dir(path: str) -> None:
        try:
            d = Path(path).parent
            d.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

    def _kb_registry_path_from_config(self) -> str:
        """Preferred JSON registry path colocated with configured DB or data file."""
        # If graph_db is JSON and has data_file, place alongside
        try:
            if self.config and (self.config.graph_db.db_type or "").lower() == "json":
                data_file = getattr(self.config.graph_db, "data_file", None)
                if data_file:
                    df = Path(str(data_file))
                    return str(df.parent / "knowledge_bases.json")
        except Exception:
            pass

        # If SQLite configured, put JSON in same database dir
        try:
            for dbc in (getattr(self.config, "cache_db", None), getattr(self.config, "graph_db", None)):
                if dbc and (getattr(dbc, "db_type", None) or "").lower() == "sqlite" and getattr(dbc, "db_location", None):
                    p = Path(str(dbc.db_location))
                    return str(p.parent / "knowledge_bases.json")
        except Exception:
            pass

        # Fallback to legacy default
        return self._resolve_kb_registry_path()

    def _kb_registry_read(self) -> List[Dict[str, Any]]:
        try:
            with open(self._kb_registry_path, "r", encoding="utf-8") as f:
                data = _json.load(f) or {}
            return list(data.get("items") or [])
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.warning(f"Failed to read KB registry: {e}")
            return []

    def _kb_registry_write(self, items: List[Dict[str, Any]]) -> None:
        try:
            with open(self._kb_registry_path, "w", encoding="utf-8") as f:
                _json.dump({"items": items}, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            logger.error(f"Failed to write KB registry: {e}")

    # --- Agent construction (CSV analysis) ---
    def _build_csv_agent(self):
        """Return a CSV analysis agent instance for pipeline steps.

        Kept lightweight and constructed on demand to avoid heavy imports at init.
        """
        try:
            from knowledge_graph.agent.agent import CsvAnalysisAgent
            return CsvAnalysisAgent()
        except Exception:
            # If agent fails to import, return None so steps skip gracefully
            logger.warning("CSV agent unavailable; skipping agent-driven steps")
            return None

    @staticmethod
    def _slugify(name: str) -> str:
        s = (name or "").strip().lower()
        s = _re.sub(r"[^a-z0-9]+", "-", s)
        s = _re.sub(r"-+", "-", s)
        return s.strip("-") or "kb"

    # --- Bulk ingestion wrapper ---
    def bulk_add_documents(
        self,
        root: str,
        glob: str = "**/*.md",
        *,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        concurrency: int = 1,
        skip_existing: bool = True,
        force_structured_markdown: bool = True,
    ) -> list[dict]:
        """Discover and ingest many markdown files under a directory.

        Returns a list of per-file result dicts {path, id?, ok?, skipped?, chunks?, elapsed_ms, error?}.
        """
        pipeline_overrides = None
        if force_structured_markdown:
            # Base settings from config, but force markdown chunker
            dp = getattr(self.config, 'document_pipeline', None)
            pipeline_overrides = DocumentPipelineConfig(
                enable_enrichment=getattr(dp, 'enable_enrichment', True) if dp else True,
                enable_kg_extraction=getattr(dp, 'enable_kg_extraction', True) if dp else True,
                enable_persistence=True,
                chunk_size=getattr(dp, 'chunk_size', 1000) if dp else 1000,
                chunk_overlap=getattr(dp, 'chunk_overlap', 200) if dp else 200,
                chunker_type='structured_markdown',
            )

        return self.document_service.add_documents_from_dir(
            root,
            glob=glob,
            domain=domain,
            tags=tags,
            concurrency=concurrency,
            skip_existing=skip_existing,
            pipeline_overrides=pipeline_overrides,
        )

    def get_cached_document(self,document_id):
        document_object = self.sql_lite.document_repository().get_document(document_id)
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
        logger.info(f"Extracting knowledge graph JSON from: {document_path}")
        
        try:
            pipeline_settings = getattr(self.config, 'document_pipeline', None)
            json_pipeline_config = DocumentPipelineConfig(
                enable_enrichment=getattr(pipeline_settings, 'enable_enrichment', True),
                enable_kg_extraction=getattr(pipeline_settings, 'enable_kg_extraction', True),
                enable_persistence=False,
                chunk_size=getattr(pipeline_settings, 'chunk_size', 1000),
                chunk_overlap=getattr(pipeline_settings, 'chunk_overlap', 200),
                chunker_type=getattr(pipeline_settings, 'chunker_type', 'auto'),
            )

            services = DocumentPipelineServices(
                llm_service=self.llm_service,
                kg_service=self.knowledge_graph_service,
                db_client=None,  # No longer using cache_db, persistence handled via sql_lite
                llm_provider=self.llm_provider,
                agent_service=self._build_csv_agent(),
            )
            transient_pipeline = PipelineFactory.for_file(document_path, services, config=json_pipeline_config)

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
        snapshot = self.sql_lite.graph_repository().get_graph_snapshot()
        return {
            'query': query_text,
            'entities': snapshot.get('nodes', []),
            'relationships': snapshot.get('edges', []),
            'total_results': len(snapshot.get('nodes', [])) + len(snapshot.get('edges', []))
        }

    
    def get_all_document_ids(self) -> List[str]:
        """
        Get all unique document IDs from entities.
        
        Returns:
            List of unique document IDs
        """
        snapshot = self.sql_lite.graph_repository().get_graph_snapshot()
        return [doc.get("id") for doc in snapshot.get("documents", [])]

    def get_graph_snapshot(self, document_id: Optional[str] = None) -> Dict[str, Any]:
        """Return a GraphSnapshot derived from the SQLite persistence layer."""
        try:
            return self.sql_lite.graph_repository().get_graph_snapshot(document_id=document_id)
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
        # sql_lite repositories use connection-per-operation, no explicit close needed
        # But we can clear any cached resources if needed
        logger.info("KnowledgeGraphClient closed")

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

    
