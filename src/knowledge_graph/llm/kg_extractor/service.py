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
from datetime import datetime

from kg_gen import KGGen



logger = logging.getLogger(__name__)

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
                    self.kg_gen = KGGen(
                        model=f"openai/{model_name}",  # Use openai/model format like quickstart
                        api_key=api_key,
                        # api_base=self.config.get('base_url'),  # Optional custom URL
                    )
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
        track_metadata: bool = False
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
                entities, relations = self._kg_gen_extract(text, context, strategy)
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

    def _kg_gen_extract(self, text: str, context: Optional[str], strategy: str) -> tuple[Set[str], List[tuple]]:
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
            
            # Extract entities and relations like quickstart
            entities = set(graph.entities) if hasattr(graph, 'entities') else set()
            
            # Convert relations to tuple format
            relations = []
            if hasattr(graph, 'relations'):
                relations = list(graph.relations)
            
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
        result = self.extract_from_text(text, context=context, track_metadata=True)

        # Update document with results
        document.knowledge_graph = result
        document.kg_extraction_metadata = result.get('metadata', {})
        document.is_kg_extracted = True
        document.kg_extracted_at = datetime.now()

        return result

    def extract_from_chunks(self, chunks: List[str], document_id: str) -> Dict[str, Any]:
        """
        Extract knowledge graph from text chunks and merge results

        Args:
            chunks: List of text chunks
            document_id: Document ID for context

        Returns:
            Merged knowledge graph results
        """
        all_entities = set()
        all_relations = []

        for i, chunk in enumerate(chunks):
            if chunk.strip():
                chunk_result = self.extract_from_text(chunk, context=f"Chunk {i+1} of document {document_id}")
                all_entities.update(chunk_result['entities'])
                all_relations.extend(chunk_result['relations'])

        # Remove duplicate relations
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
