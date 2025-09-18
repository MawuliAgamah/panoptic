"""
Knowledge Graph Extraction Service

Implements knowledge graph extraction from text using kg-gen or custom methods.
Follows TDD approach with comprehensive test coverage.
"""
import logging
import time
from typing import Dict, List, Set, Any, Optional
from datetime import datetime
import dspy
from kg_gen import KGGen

logger = logging.getLogger(__name__)

class KGExtractionService:
    """Service for extracting knowledge graphs from text and documents"""

    def __init__(self, llm_provider: str = "ollama", **kwargs):
        """
        Initialize KG extraction service

        Args:
            llm_provider: LLM provider to use ("openai", "ollama", etc.)
            **kwargs: Additional configuration options
        """
        self.llm_provider = llm_provider
        self.config = kwargs
        self._setup_llm()

    def _setup_llm(self):
        """Setup LLM based on provider"""
        try:
            if self.llm_provider == "ollama":
                from dspy import OllamaLocal
                self.dspy_lm = OllamaLocal(
                    model=self.config.get('model', 'llama3.2:3b'),
                    max_tokens=self.config.get('max_tokens', 1000)
                )
            elif self.llm_provider == "openai":
                import os
                if not os.getenv('OPENAI_API_KEY'):
                    raise ValueError("OPENAI_API_KEY environment variable is required for OpenAI provider")

                self.dspy_lm = dspy.LM(
                    model=f"openai/{self.config.get('model', 'gpt-3.5-turbo')}",
                    max_tokens=self.config.get('max_tokens', 1000),
                    temperature=0.0
                )
            else:
                logger.warning(f"Unsupported LLM provider: {self.llm_provider}. Using mock extraction.")
                self.dspy_lm = None

            # Set up kg-gen if LLM is available
            if self.dspy_lm:
                dspy.settings.configure(lm=self.dspy_lm)

                # KGGen expects a model string, not a dspy.LM object
                if self.llm_provider == "openai":
                    model_string = f"openai/{self.config.get('model', 'gpt-3.5-turbo')}"
                elif self.llm_provider == "ollama":
                    model_string = self.config.get('model', 'llama3.2:3b')
                else:
                    model_string = "openai/gpt-3.5-turbo"  # fallback

                self.kg_gen = KGGen(
                    model=model_string,
                    temperature=0.0
                )
                self.is_configured = True
            else:
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

        # Use real kg-gen extraction if available, otherwise fallback to mock
        if self.is_configured and self.kg_gen:
            try:
                entities, relations = self._kg_gen_extract(text, context, strategy)
            except Exception as e:
                logger.warning(f"kg-gen extraction failed: {e}. Falling back to mock extraction.")
                entities = self._mock_extract_entities(text, strategy)
                relations = self._mock_extract_relations(text, entities, strategy)
        else:
            # Use mock extraction when LLM not available
            entities = self._mock_extract_entities(text, strategy)
            relations = self._mock_extract_relations(text, entities, strategy)

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
        Use kg-gen to extract entities and relations

        Args:
            text: Input text
            context: Optional context
            strategy: Extraction strategy

        Returns:
            Tuple of (entities_set, relations_list)
        """
        try:
            # Use clustering based on strategy
            use_clustering = (strategy == "detailed")

            graph_result = self.kg_gen.generate(
                input_data=text,
                chunk_size=5000,  # Process text in chunks of 5000 chars
                cluster=use_clustering  # Cluster similar entities and relations
            )

            # kg-gen returns a Graph object with .entities and .relations
            entities = set(graph_result.entities) if hasattr(graph_result, 'entities') else set()
            relations = list(graph_result.relations) if hasattr(graph_result, 'relations') else []

            return entities, relations

        except Exception as e:
            logger.error(f"kg-gen extraction failed: {e}")
            raise

    def _mock_extract_entities(self, text: str, strategy: str) -> Set[str]:
        """Mock entity extraction - will be replaced with real implementation"""
        # Simple keyword-based extraction for testing
        entities = set()

        # Common programming/ML keywords
        keywords = [
            "Python", "Machine Learning", "TensorFlow", "Google", "Artificial Intelligence",
            "programming", "language", "framework", "algorithm", "data", "science",
            "neural network", "deep learning", "AI", "ML"
        ]

        text_lower = text.lower()
        for keyword in keywords:
            if keyword.lower() in text_lower:
                entities.add(keyword)

        return entities

    def _mock_extract_relations(self, text: str, entities: Set[str], strategy: str) -> List[tuple]:
        """Mock relation extraction - will be replaced with real implementation"""
        relations = []

        # Simple pattern-based relation extraction
        entity_list = list(entities)
        for i, entity1 in enumerate(entity_list):
            for entity2 in entity_list[i+1:]:
                if entity1.lower() in text.lower() and entity2.lower() in text.lower():
                    # Create a simple relation
                    relations.append((entity1, "related_to", entity2))

        return relations

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