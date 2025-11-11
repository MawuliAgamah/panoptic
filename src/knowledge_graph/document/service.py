from typing import Optional, List
import logging
import uuid
from pathlib import Path
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from ..document_ingestion import DocumentPipeline, DocumentPipelineConfig, DocumentPipelineServices
from ..document_ingestion.pdf.steps import (
    LoadDocumentStep,
    CleanContentStep,
    ExtractCsvGraphStep,
    ChunkContentStep,
    ExtractKnowledgeGraphStep,
    PersistDocumentStep,
    RouteDocumentStep,
)
from ..document_ingestion.factory import PipelineFactory
from ..knowledge_graph.service import KnowledgeGraphService

class DocumentService:
    """Service for document operations, used by the client"""

    def __init__(
        self,
        db_client,
        llm_service=None,
        llm_provider="openai",
        pipeline_config: Optional[DocumentPipelineConfig] = None,
        kg_service=None,
    ):
        self.logger = logging.getLogger("knowledgeAgent.document")
        self.db_client = db_client
        self.llm_service = llm_service
        self.llm_provider = llm_provider

        if kg_service is not None:
            self.kg_service = kg_service
        elif db_client is not None:
            self.kg_service = KnowledgeGraphService(
                db_client=db_client,
                llm_service=llm_service,
                llm_provider=llm_provider,
            )
        else:
            self.kg_service = None

        self.pipeline_config = pipeline_config or DocumentPipelineConfig()
        self.pipeline = self._create_pipeline(self.pipeline_config)

    def _create_pipeline(self, config: DocumentPipelineConfig) -> DocumentPipeline:
        enrichment_enabled = config.enable_enrichment
        kg_enabled = config.enable_kg_extraction
        persistence_enabled = config.enable_persistence and self.db_client is not None

        # Default/general pipeline mirrors previous behavior
        services = DocumentPipelineServices(
            llm_service=self.llm_service,
            kg_service=self.kg_service,
            db_client=self.db_client,
            llm_provider=self.llm_provider,
        )
        return PipelineFactory.general_pipeline(services, config=config)

    def build_pipeline(self, config: DocumentPipelineConfig) -> DocumentPipeline:
        """Construct a new pipeline instance using the provided configuration."""
        return self._create_pipeline(config)

    def process_document(self, document_path, document_id, domain=None, tags=None, pipeline=None):
        """Run the configured pipeline and return the processed document."""
        # Choose a pipeline if none provided, based on file extension
        if pipeline is None:
            services = DocumentPipelineServices(
                llm_service=self.llm_service,
                kg_service=self.kg_service,
                db_client=self.db_client,
                llm_provider=self.llm_provider,
            )
            pipeline = PipelineFactory.for_file(document_path, services, config=self.pipeline_config)

        return pipeline.run(
            document_path=document_path,
            document_id=document_id,
            domain=domain,
            tags=tags,
        )
        
    def add_document(self, document_path, document_type=None, document_id=None, domain=None, tags=None, cache=True):
        """Add a document to the system"""
        try:
            # Generate document ID if not provided
            if document_id is None:
                document_id = str(uuid.uuid4())

            document = self.process_document(document_path, document_id, domain=domain, tags=tags)
            if document is None:
                self.logger.error("Failed to process document")
                return None
            return document.id
            
        except Exception as e:
            self.logger.error(f"Error adding document: {e}")
            return None
        
    def delete_document(self,document_id: str):
        self.db_client.delete_document(document_id)
        self.logger.info(f"Document deleted with ID: {document_id}")
        
    # --- Bulk ingestion helpers ---
    def add_documents_from_dir(
        self,
        root: str,
        glob: str = "**/*.md",
        *,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
        concurrency: int = 1,
        skip_existing: bool = True,
        pipeline_overrides: Optional[DocumentPipelineConfig] = None,
    ) -> list[dict]:
        """
        Bulk-ingest documents discovered under a directory.

        - Discovers files by glob (default: "**/*.md").
        - Optionally skips files that already exist in SQLite (by file_path).
        - Uses a dedicated pipeline instance so overrides don't affect the default.
        - Returns a per-file result summary with timings.
        """
        root_path = Path(root)
        if not root_path.exists():
            self.logger.error("Bulk ingest root does not exist: %s", root)
            return []

        files = [p for p in root_path.rglob(glob) if p.is_file()]
        self.logger.info(
            "[bulk] Discovered %d files under %s with glob '%s'",
            len(files),
            root_path,
            glob,
        )

        results: list[dict] = []

        # Build a pipeline with overrides (e.g., force structured_markdown)
        base_cfg = self.pipeline_config
        cfg = DocumentPipelineConfig(
            enable_enrichment=pipeline_overrides.enable_enrichment if pipeline_overrides else base_cfg.enable_enrichment,
            enable_kg_extraction=pipeline_overrides.enable_kg_extraction if pipeline_overrides else base_cfg.enable_kg_extraction,
            enable_persistence=pipeline_overrides.enable_persistence if pipeline_overrides else base_cfg.enable_persistence,
            chunk_size=pipeline_overrides.chunk_size if pipeline_overrides else base_cfg.chunk_size,
            chunk_overlap=pipeline_overrides.chunk_overlap if pipeline_overrides else base_cfg.chunk_overlap,
            chunker_type=pipeline_overrides.chunker_type if pipeline_overrides else base_cfg.chunker_type,
        )
        pipeline = self.build_pipeline(cfg)

        def _process(path: Path) -> dict:
            started = time.time()
            doc_path = str(path)
            try:
                if skip_existing and hasattr(self.db_client, 'sqlite_service') and self.db_client.sqlite_service:
                    repo = self.db_client.sqlite_service.repository
                    if repo.doc_exists(doc_path):
                        elapsed_ms = int((time.time() - started) * 1000)
                        self.logger.info("[bulk] Skipping existing: %s (%d ms)", doc_path, elapsed_ms)
                        return {"path": doc_path, "skipped": True, "elapsed_ms": elapsed_ms}

                doc_id = str(uuid.uuid4())
                self.logger.info("[bulk] Processing: %s", doc_path)
                document = self.process_document(doc_path, doc_id, domain=domain, tags=tags, pipeline=pipeline)
                elapsed_ms = int((time.time() - started) * 1000)
                if document is None:
                    self.logger.error("[bulk] Failed: %s (%d ms)", doc_path, elapsed_ms)
                    return {"path": doc_path, "ok": False, "elapsed_ms": elapsed_ms}
                chunk_count = len(getattr(document, 'textChunks', []) or [])
                self.logger.info(
                    "[bulk] Done: %s id=%s chunks=%d (%d ms)",
                    doc_path,
                    document.id,
                    chunk_count,
                    elapsed_ms,
                )
                return {
                    "path": doc_path,
                    "id": document.id,
                    "ok": True,
                    "chunks": chunk_count,
                    "elapsed_ms": elapsed_ms,
                }
            except Exception as exc:
                elapsed_ms = int((time.time() - started) * 1000)
                self.logger.exception("[bulk] Error processing %s (%d ms): %s", doc_path, elapsed_ms, exc)
                return {"path": doc_path, "ok": False, "error": str(exc), "elapsed_ms": elapsed_ms}

        if concurrency and concurrency > 1:
            self.logger.info("[bulk] Running with concurrency=%d", concurrency)
            with ThreadPoolExecutor(max_workers=concurrency) as pool:
                future_map = {pool.submit(_process, p): p for p in files}
                for fut in as_completed(future_map):
                    results.append(fut.result())
        else:
            for p in files:
                results.append(_process(p))

        # Summary
        ok = sum(1 for r in results if r.get("ok"))
        skipped = sum(1 for r in results if r.get("skipped"))
        failed = sum(1 for r in results if (not r.get("ok") and not r.get("skipped")))
        self.logger.info("[bulk] Finished. ok=%d skipped=%d failed=%d", ok, skipped, failed)
        return results


    
    
