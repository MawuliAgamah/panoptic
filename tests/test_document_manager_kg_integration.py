"""
Test KG integration in DocumentManager

This test validates that the DocumentManager correctly integrates KG extraction
into the complete document processing pipeline.
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.document.manager.document_manager import DocumentManager
from knowledge_graph.llm.kg_extractor.service import KGExtractionService


class TestDocumentManagerKGIntegration:
    """Test KG integration in DocumentManager"""

    def setup_method(self):
        """Setup test environment"""
        self.test_document_path = "/Users/mawuliagamah/obsidian vaults/Software Company/3. BookShelf/Books/An Illustrated Book of Bad Arguments.md"

        # Mock LLM service
        self.mock_llm_service = MagicMock()
        self.mock_llm_service.extract_topics.return_value = {"topics": ["logic", "fallacies", "reasoning"]}
        self.mock_llm_service.extract_keywords.return_value = {"keywords": ["argument", "critical-thinking", "philosophy"]}

        # Create KG service with mock provider
        self.kg_service = KGExtractionService(llm_provider="mock")

        # Create document manager with both services
        self.document_manager = DocumentManager(
            llm_service=self.mock_llm_service,
            kg_service=self.kg_service
        )

    def test_document_manager_kg_initialization(self):
        """Test that DocumentManager properly initializes with KG service"""
        # Test with explicit KG service
        manager_with_kg = DocumentManager(
            llm_service=self.mock_llm_service,
            kg_service=self.kg_service
        )
        assert manager_with_kg.kg_service is not None
        assert manager_with_kg.kg_service == self.kg_service

        # Test with default KG service
        manager_default_kg = DocumentManager(llm_service=self.mock_llm_service)
        assert manager_default_kg.kg_service is not None
        assert isinstance(manager_default_kg.kg_service, KGExtractionService)

    def test_extract_knowledge_graph_method(self):
        """Test the extract_knowledge_graph method"""
        # Create a test document
        document = self.document_manager.make_new_document(self.test_document_path, "test_kg_doc")
        assert document is not None

        # Clean the document first
        document = self.document_manager.clean_document(document)
        assert document.clean_content is not None

        # Test KG extraction
        document = self.document_manager.extract_knowledge_graph(document)

        # Verify KG extraction results
        assert document.is_kg_extracted == True
        assert document.knowledge_graph is not None
        assert 'entities' in document.knowledge_graph
        assert 'relations' in document.knowledge_graph
        assert document.kg_extracted_at is not None
        assert document.kg_extraction_metadata is not None

    def test_document_level_vs_chunk_level_decision(self):
        """Test that the manager makes correct processing decisions"""
        # Create a test document
        document = self.document_manager.make_new_document(self.test_document_path, "decision_test_doc")
        document = self.document_manager.clean_document(document)

        # This document should use document-level processing (small size)
        should_use_document_level = document.should_use_document_level_kg()
        assert should_use_document_level == True

        # Extract KG and verify strategy
        document = self.document_manager.extract_knowledge_graph(document)

        # Check metadata for strategy used
        metadata = document.kg_extraction_metadata
        assert 'strategy_used' in metadata

        # For this small document, it should use document-level strategy
        # (The metadata is set by extract_from_document method)
        print(f"KG extraction strategy: {metadata.get('strategy_used', 'document-level (implicit)')}")

    def test_chunk_level_processing_simulation(self):
        """Test chunk-level processing by forcing a low token limit"""
        # Create a test document
        document = self.document_manager.make_new_document(self.test_document_path, "chunk_test_doc")
        document = self.document_manager.clean_document(document)

        # Force chunk-level processing by setting a very low token limit
        document.kg_extraction_token_limit = 10  # Very low limit

        # Now the document should require chunk-level processing
        should_use_document_level = document.should_use_document_level_kg()
        assert should_use_document_level == False

        # Extract KG - this will trigger chunk-level processing
        document = self.document_manager.extract_knowledge_graph(document)

        # Verify results
        assert document.is_kg_extracted == True
        assert document.knowledge_graph is not None
        assert document.kg_extraction_metadata is not None

        # Should have chunk-level metadata
        metadata = document.kg_extraction_metadata
        assert metadata['strategy_used'] == 'chunk-level'
        assert 'chunk_count' in metadata

    def test_process_document_complete_pipeline(self):
        """Test the complete document processing pipeline with KG extraction"""
        # Process document through complete pipeline
        document = self.document_manager.process_document_complete(
            document_path=self.test_document_path,
            document_id="complete_pipeline_test",
            enable_kg_extraction=True,
            enable_enrichment=False  # Skip enrichment for faster testing
        )

        # Verify all processing steps were completed
        assert document is not None
        assert document.is_parsed == True
        assert document.is_preprocessed == True  # Document was cleaned
        assert document.is_metadata_generated == True
        assert document.is_kg_extracted == True
        assert document.is_chunked == True

        # Verify content processing
        assert document.raw_content is not None
        assert document.clean_content is not None
        assert len(document.clean_content) > 0

        # Verify KG extraction
        assert document.knowledge_graph is not None
        assert 'entities' in document.knowledge_graph
        assert 'relations' in document.knowledge_graph
        assert len(document.knowledge_graph['entities']) > 0

        # Verify metadata generation
        assert document.metadata.tags is not None
        assert document.metadata.categories is not None
        assert document.metadata.word_count > 0

        # Verify chunking
        assert len(document.textChunks) > 0

    def test_process_document_complete_without_kg(self):
        """Test complete pipeline with KG extraction disabled"""
        document = self.document_manager.process_document_complete(
            document_path=self.test_document_path,
            document_id="no_kg_test",
            enable_kg_extraction=False,
            enable_enrichment=False
        )

        # Verify document was processed
        assert document is not None
        assert document.is_parsed == True
        assert document.is_preprocessed == True
        assert document.is_metadata_generated == True
        assert document.is_chunked == True

        # Verify KG extraction was skipped
        assert document.is_kg_extracted == False
        assert document.knowledge_graph is None

    def test_kg_extraction_error_handling(self):
        """Test error handling in KG extraction"""
        # Create document with invalid content
        document = self.document_manager.make_new_document(self.test_document_path, "error_test_doc")
        document = self.document_manager.clean_document(document)

        # Set invalid content to trigger error
        document.clean_content = None
        document.raw_content = None

        # Extract KG - should handle gracefully
        result_document = self.document_manager.extract_knowledge_graph(document)

        # Should be marked as processed with empty results
        assert result_document.is_kg_extracted == True
        assert result_document.knowledge_graph is not None
        assert result_document.knowledge_graph['entities'] == set()
        assert result_document.knowledge_graph['relations'] == []

    def test_kg_service_integration_with_real_content(self):
        """Test KG service integration with actual document content"""
        # Process real document
        document = self.document_manager.make_new_document(self.test_document_path, "real_content_test")
        document = self.document_manager.clean_document(document)

        # Extract KG
        document = self.document_manager.extract_knowledge_graph(document)

        # Verify extraction worked on real content
        assert document.is_kg_extracted == True
        entities = document.knowledge_graph['entities']
        relations = document.knowledge_graph['relations']

        print(f"Extracted from real document: {len(entities)} entities, {len(relations)} relations")
        print(f"Sample entities: {list(entities)[:10]}")  # Show first 10

        # Should extract some entities from the logical fallacies content
        assert len(entities) > 0

        # Check for expected domain concepts (case-insensitive)
        entity_names_lower = {e.lower() for e in entities}
        expected_concepts = ['argument', 'logic', 'reasoning', 'fallacy']
        found_concepts = [concept for concept in expected_concepts if any(concept in e for e in entity_names_lower)]
        print(f"Found expected concepts: {found_concepts}")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])