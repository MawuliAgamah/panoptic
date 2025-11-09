"""
Knowledge Graph Extraction Service

Implements knowledge graph extraction from text using kg-gen or custom methods.
Follows TDD approach with comprehensive test coverage.
"""
import logging
import time
import os
import tempfile
from typing import Dict, List, Set, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from threading import Lock

from kg_gen import KGGen

logger = logging.getLogger(__name__)

# Reuse a single KGGen instance across requests to avoid repeated DSPy configuration.
_kggen_lock: Lock = Lock()
_kggen_instance: Optional[KGGen] = None
_kggen_signature: Optional[tuple[str, str]] = None


def _get_shared_kggen(model: str, api_key: str) -> KGGen:
    """Return a process-wide KGGen instance keyed by model and API key."""
    global _kggen_instance, _kggen_signature

    signature = (model, api_key)
    with _kggen_lock:
        if _kggen_instance is None or _kggen_signature != signature:
            _kggen_instance = KGGen(model=model, api_key=api_key)
            _kggen_signature = signature
        return _kggen_instance

class KGExtractionService:
    """Service for extracting knowledge graphs from text and documents"""

    def __init__(self, llm_provider: str = "openai", **kwargs):
        """
        Initialize KG extraction service

        Args:
            llm_provider: LLM provider to use ("openai", "ollama", etc.)
            **kwargs: Additional configuration options
        """
        self.llm_provider = llm_provider
        self.config = kwargs
        self.kg_gen = None
        self.is_configured = False
        # Parallelism controls
        self.max_concurrent_chunks: int = int(kwargs.get("max_concurrent_chunks", 4) or 4)
        
        # Setup LLM (simplified without DSPy)
        self._setup_llm()


    def _setup_llm(self):
        """Setup LLM based on provider - simplified like quickstart"""
        try:
            if self.llm_provider == "openai":
                # Get API key
                api_key = os.getenv('OPENAI_API_KEY')
                if not api_key:
                    raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")

                # Simple KGGen initialization like the quickstart
                model_name = self.config.get('model', 'gpt-4o-mini')
                
                try:
                    model_identifier = f"openai/{model_name}"
                    self.kg_gen = _get_shared_kggen(model_identifier, api_key)
                    self.is_configured = True
                    logger.info(f"KGGen initialized successfully with model: openai/{model_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize KGGen: {e}")
                    self.kg_gen = None
                    self.is_configured = False
                    
            else:
                logger.warning(f"Only OpenAI provider supported in simplified mode. Got: {self.llm_provider}")
                self.kg_gen = None
                self.is_configured = False

        except Exception as e:
            logger.warning(f"Failed to initialize LLM ({self.llm_provider}): {e}. Using mock extraction.")
            self.kg_gen = None
            self.is_configured = False

    def extract_from_text(
        self,
        text: str,
        context: Optional[str] = None,
        strategy: str = "simple",
        track_metadata: bool = False,
        *,
        log_label: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Extract knowledge graph from text

        Args:
            text: Input text to extract from
            context: Optional context for better extraction
            strategy: Extraction strategy ("simple", "detailed")
            track_metadata: Whether to track extraction metadata

        Returns:
            Dictionary with 'entities' (set), 'relations' (list), and optionally 'metadata'
        """
        start_time = time.time()

        # Handle edge cases
        if not text or text.strip() == "":
            result = {'entities': set(), 'relations': []}
            if track_metadata:
                result['metadata'] = {
                    'extraction_time': time.time() - start_time,
                    'entity_count': 0,
                    'relation_count': 0,
                    'strategy_used': strategy
                }
            return result

        if text is None:
            result = {'entities': set(), 'relations': []}
            if track_metadata:
                result['metadata'] = {
                    'extraction_time': time.time() - start_time,
                    'entity_count': 0,
                    'relation_count': 0,
                    'strategy_used': strategy
                }
            return result

        # For very short text, return minimal extraction
        if len(text.strip()) <= 10:
            result = {'entities': set(), 'relations': []}
            if track_metadata:
                result['metadata'] = {
                    'extraction_time': time.time() - start_time,
                    'entity_count': 0,
                    'relation_count': 0,
                    'strategy_used': strategy
                }
            return result

        if not self.is_configured or not self.kg_gen:
            logger.warning("KGExtractionService is not fully configured; returning empty extraction")
            entities: Set[str] = set()
            relations: List[tuple] = []
        else:
            try:
                entities, relations = self._kg_gen_extract(text, context, strategy, log_label=log_label)
            except Exception as e:
                logger.error(f"kg-gen extraction failed: {e}")
                entities = set()
                relations = []

        result = {
            'entities': entities,
            'relations': relations
        }

        if track_metadata:
            result['metadata'] = {
                'extraction_time': time.time() - start_time,
                'entity_count': len(entities),
                'relation_count': len(relations),
                'strategy_used': strategy
            }

        return result

    def _kg_gen_extract(self, text: str, context: Optional[str], strategy: str, *, log_label: Optional[str] = None) -> tuple[Set[str], List[tuple]]:
        """
        Use kg-gen to extract entities and relations - simplified like quickstart
        """
        if not self.kg_gen:
            raise RuntimeError("kg_gen not configured")

        try:
            # Simple generation like the quickstart
            graph = self.kg_gen.generate(
                input_data=text,
                context=context,  # Pass context directly
            )
            
            # Normalize entities into a set of string names
            entities: Set[str] = set()
            if hasattr(graph, 'entities') and graph.entities:
                for ent in graph.entities:
                    # ent may be a string or an object with name/label
                    try:
                        name = getattr(ent, 'name', None) or getattr(ent, 'label', None) or (ent if isinstance(ent, str) else str(ent))
                        name = str(name).strip()
                        if name:
                            entities.add(name)
                    except Exception:
                        continue

            # Convert relations to tuple format (source, predicate, target)
            relations: List[tuple] = []
            if hasattr(graph, 'relations') and graph.relations:
                for rel in graph.relations:
                    try:
                        if isinstance(rel, (list, tuple)) and len(rel) >= 3:
                            source, predicate, target = rel[:3]
                        else:
                            source = getattr(rel, 'source', None) or getattr(rel, 'subject', None)
                            predicate = getattr(rel, 'relation', None) or getattr(rel, 'predicate', None)
                            target = getattr(rel, 'target', None) or getattr(rel, 'object', None)
                        if source and predicate and target:
                            relations.append((str(source).strip(), str(predicate).strip(), str(target).strip()))
                    except Exception:
                        continue
            
            if log_label:
                logger.info(f"KG generation complete ({log_label}): {len(entities)} entities, {len(relations)} relations")
            else:
                logger.info(f"KG generation complete: {len(entities)} entities, {len(relations)} relations")
            
            return entities, relations
            
        except Exception as e:
            logger.error(f"kg-gen extraction failed: {e}")
            return set(), []

   
    def extract_from_document(self, document) -> Dict[str, Any]:
        """
        Extract knowledge graph from Document object

        Args:
            document: Document object to extract from

        Returns:
            Dictionary with entities and relations, updates document with KG data
        """
        # Use clean_content if available, otherwise raw_content
        text = document.clean_content or document.raw_content

        # Generate context from document metadata
        context = document.get_kg_extraction_context()

        # Extract knowledge graph
        result = self.extract_from_text(text, context=context, track_metadata=True, log_label="document")

        # Update document with results
        document.knowledge_graph = result
        document.kg_extraction_metadata = result.get('metadata', {})
        document.is_kg_extracted = True
        document.kg_extracted_at = datetime.now()

        return result

    def extract_from_chunks(self, chunks: List[Any], document_id: str, contexts: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Extract knowledge graph from text chunks and merge results.

        Accepts either:
        - chunks: List[str] and optional contexts: List[str] of same length
        - chunks: List[tuple[str, str]] where tuple = (text, context)

        Args:
            chunks: List of chunk texts or (text, context) tuples
            document_id: Document ID for context fallback
            contexts: Optional list of contexts matching the order of `chunks`

        Returns:
            Merged knowledge graph results
        """
        all_entities = set()
        all_relations: List[tuple] = []

        # Normalize input into list of (text, context)
        normalized: List[tuple[str, Optional[str]]] = []
        for idx, item in enumerate(chunks):
            if isinstance(item, tuple) and len(item) >= 1:
                text = item[0]
                ctx = item[1] if len(item) > 1 else None
            else:
                text = str(item)
                ctx = contexts[idx] if contexts and idx < len(contexts) else None
            normalized.append((text, ctx))

        total = len(normalized)

        # Fast path: small number of chunks or parallelism disabled
        if total <= 1 or (self.max_concurrent_chunks is not None and self.max_concurrent_chunks <= 1):
            for i, (chunk_text, ctx) in enumerate(normalized):
                if not chunk_text or not chunk_text.strip():
                    continue
                effective_ctx = ctx or f"Chunk {i+1} of document {document_id}"
                chunk_result = self.extract_from_text(
                    chunk_text,
                    context=effective_ctx,
                    log_label=f"chunk {i+1}/{total}"
                )
                all_entities.update(chunk_result.get('entities', set()))
                all_relations.extend(chunk_result.get('relations', []))
        else:
            # Threaded parallelism (I/O-bound LLM calls)
            max_workers = max(1, min(self.max_concurrent_chunks, total))
            logger.info(
                f"Parallel KG extraction for {total} chunks with max_workers={max_workers}"
            )

            def _task(i_and_item: tuple[int, tuple[str, Optional[str]]]) -> Dict[str, Any]:
                i, (chunk_text, ctx) = i_and_item
                if not chunk_text or not chunk_text.strip():
                    return {'entities': set(), 'relations': []}
                effective_ctx = ctx or f"Chunk {i+1} of document {document_id}"
                return self.extract_from_text(
                    chunk_text,
                    context=effective_ctx,
                    log_label=f"chunk {i+1}/{total}"
                )

            with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="kg-chunk") as executor:
                futures = [executor.submit(_task, (i, item)) for i, item in enumerate(normalized)]
                for fut in as_completed(futures):
                    try:
                        chunk_result = fut.result()
                    except Exception as e:
                        logger.error(f"Chunk extraction task failed: {e}")
                        continue
                    all_entities.update(chunk_result.get('entities', set()))
                    all_relations.extend(chunk_result.get('relations', []))

        unique_relations = list(set(all_relations))
        return {
            'entities': all_entities,
            'relations': unique_relations
        }

    def extract_and_save(
        self,
        text: str,
        document_id: str,
        db_client,
        context: Optional[str] = None
    ) -> bool:
        """
        Extract knowledge graph and save to database

        Args:
            text: Input text
            document_id: Document identifier
            db_client: Database client for storage
            context: Optional context

        Returns:
            True if successful
        """
        try:
            # Extract knowledge graph
            result = self.extract_from_text(text, context=context)

            # Save to database
            success = db_client.save_knowledge_graph(document_id, result)

            return success
        except Exception as e:
            logger.error(f"Error in extract_and_save: {e}")
            return False

    def extract_batch(self, documents: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """
        Extract knowledge graphs from multiple documents

        Args:
            documents: List of documents with 'id' and 'text' keys

        Returns:
            List of extraction results with document_id
        """
        results = []

        for doc in documents:
            doc_id = doc.get('id')
            text = doc.get('text', '')

            result = self.extract_from_text(text)
            result['document_id'] = doc_id

            results.append(result)

        return results
