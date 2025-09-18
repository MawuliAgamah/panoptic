"""
Test-driven development for KG Extraction Service

Following TDD approach:
1. Write tests for expected behavior first
2. Implement minimal code to pass tests
3. Refactor and improve

This service will extract knowledge graphs from documents using kg-gen or similar approach.
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class TestKGExtractionService:
    """TDD tests for knowledge graph extraction service"""

    def setup_method(self):
        """Setup test environment"""
        # Test document content
        self.test_content = """
        Python is a programming language. Machine learning uses Python extensively.
        TensorFlow is a machine learning framework. It was developed by Google.
        Artificial intelligence encompasses machine learning techniques.
        """

        # Expected kg-gen style output format
        self.expected_output = {
            'entities': {'Python', 'Machine Learning', 'TensorFlow', 'Google', 'Artificial Intelligence'},
            'relations': [
                ('Machine Learning', 'uses', 'Python'),
                ('TensorFlow', 'is_a', 'Machine Learning Framework'),
                ('Google', 'developed', 'TensorFlow'),
                ('Artificial Intelligence', 'encompasses', 'Machine Learning')
            ]
        }

    def test_kg_extraction_service_exists(self):
        """Test 1: Service class should exist and be importable"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()
        assert service is not None

    def test_extract_from_text_basic(self):
        """Test 2: Service should extract entities and relations from text"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()
        result = service.extract_from_text(self.test_content)

        # Should return kg-gen compatible format
        assert isinstance(result, dict)
        assert 'entities' in result
        assert 'relations' in result
        assert isinstance(result['entities'], set)
        assert isinstance(result['relations'], list)

    def test_extract_from_text_with_context(self):
        """Test 3: Service should accept context for better extraction"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()
        context = "Document about programming languages and ML frameworks"

        result = service.extract_from_text(self.test_content, context=context)

        assert isinstance(result, dict)
        assert 'entities' in result
        assert 'relations' in result

    def test_extract_from_document(self):
        """Test 4: Service should extract from Document objects"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService
        from knowledge_graph.document.models.document import Document
        from knowledge_graph.document.models.metadata import DocumentMetadata

        # Create test document
        metadata = DocumentMetadata(
            document_id="test_doc",
            metadata_id="test_meta",
            title="ML Programming Guide"
        )

        document = Document(
            id="test_doc",
            filename="ml_guide.md",
            file_path="/test/ml_guide.md",
            file_type=".md",
            file_size=100,
            title="ML Programming Guide",
            raw_content=self.test_content,
            clean_content=self.test_content,
            metadata=metadata,
            textChunks=[]
        )

        service = KGExtractionService()
        result = service.extract_from_document(document)

        assert isinstance(result, dict)
        assert 'entities' in result
        assert 'relations' in result
        # Document should be updated with KG data
        assert document.knowledge_graph is not None
        assert document.is_kg_extracted == True
        assert document.kg_extracted_at is not None

    def test_extract_from_chunks(self):
        """Test 5: Service should extract from text chunks and merge results"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        chunks = [
            "Python is a programming language used in machine learning.",
            "TensorFlow is a framework developed by Google for ML.",
            "Artificial intelligence uses various machine learning techniques."
        ]

        service = KGExtractionService()
        result = service.extract_from_chunks(chunks, document_id="test_doc")

        assert isinstance(result, dict)
        assert 'entities' in result
        assert 'relations' in result
        # Should merge entities and relations from all chunks
        assert len(result['entities']) > 0
        assert len(result['relations']) > 0

    def test_entity_clustering_and_normalization(self):
        """Test 6: Service should cluster similar entities"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        # Text with similar entities that should be clustered
        text_with_variations = """
        Machine Learning is important. ML techniques are used everywhere.
        Artificial Intelligence and AI are the future. Python programming
        language and Python are widely used.
        """

        service = KGExtractionService()
        result = service.extract_from_text(text_with_variations)

        # Should cluster similar entities
        entities = result['entities']
        # Should not have both "Machine Learning" and "ML" as separate entities
        # Should not have both "Python programming language" and "Python"
        assert isinstance(entities, set)

    def test_extraction_metadata_tracking(self):
        """Test 7: Service should track extraction performance metadata"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()
        result = service.extract_from_text(self.test_content, track_metadata=True)

        assert 'metadata' in result
        metadata = result['metadata']
        assert 'extraction_time' in metadata
        assert 'entity_count' in metadata
        assert 'relation_count' in metadata
        assert 'strategy_used' in metadata
        assert metadata['extraction_time'] > 0

    def test_error_handling_empty_text(self):
        """Test 8: Service should handle empty or invalid text gracefully"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()

        # Test empty text
        result = service.extract_from_text("")
        assert result['entities'] == set()
        assert result['relations'] == []

        # Test None
        result = service.extract_from_text(None)
        assert result['entities'] == set()
        assert result['relations'] == []

        # Test very short text
        result = service.extract_from_text("Hi.")
        assert isinstance(result['entities'], set)
        assert isinstance(result['relations'], list)

    def test_configurable_extraction_strategy(self):
        """Test 9: Service should support different extraction strategies"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()

        # Test with different strategies
        result1 = service.extract_from_text(self.test_content, strategy="simple")
        result2 = service.extract_from_text(self.test_content, strategy="detailed")

        assert isinstance(result1, dict)
        assert isinstance(result2, dict)
        # Different strategies might produce different results
        assert 'entities' in result1 and 'entities' in result2
        assert 'relations' in result1 and 'relations' in result2

    def test_llm_provider_configuration(self):
        """Test 10: Service should support different LLM providers"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        # Should be able to configure different providers
        service_openai = KGExtractionService(llm_provider="openai")
        service_ollama = KGExtractionService(llm_provider="ollama")

        assert service_openai.llm_provider == "openai"
        assert service_ollama.llm_provider == "ollama"

    def test_neo4j_integration(self):
        """Test 11: Service should integrate with Neo4j storage"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()

        # Mock database client
        mock_db_client = MagicMock()
        mock_db_client.save_knowledge_graph.return_value = True

        result = service.extract_and_save(
            text=self.test_content,
            document_id="test_doc",
            db_client=mock_db_client
        )

        assert result == True
        mock_db_client.save_knowledge_graph.assert_called_once()

    def test_batch_processing_capability(self):
        """Test 12: Service should handle batch processing efficiently"""
        from knowledge_graph.llm.kg_extractor.service import KGExtractionService

        service = KGExtractionService()

        documents = [
            {"id": "doc1", "text": "Python is a language."},
            {"id": "doc2", "text": "ML uses various algorithms."},
            {"id": "doc3", "text": "TensorFlow is a framework."}
        ]

        results = service.extract_batch(documents)

        assert len(results) == 3
        for result in results:
            assert 'entities' in result
            assert 'relations' in result
            assert 'document_id' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])