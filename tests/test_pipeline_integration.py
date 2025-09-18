"""
Integration test for complete pipeline: Document processing + KG extraction + Neo4j storage

This test demonstrates the complete flow from raw document to knowledge graph storage.
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock, patch

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.document.models.document import Document
from knowledge_graph.document.models.metadata import DocumentMetadata
from knowledge_graph.llm.kg_extractor.service import KGExtractionService
from knowledge_graph.core.db.db_client import DatabaseClient

class TestPipelineIntegration:
    """Integration tests for the complete document -> KG -> storage pipeline"""

    def setup_method(self):
        """Setup test environment"""
        # Sample document content with entities and relationships
        self.test_content = """
        Python is a popular programming language used in artificial intelligence and machine learning.
        TensorFlow is an open-source machine learning framework developed by Google.
        PyTorch is another machine learning framework created by Facebook.
        Both TensorFlow and PyTorch are written in Python and C++.
        Data scientists use these frameworks to build neural networks for deep learning applications.
        """

        # Create test document
        self.metadata = DocumentMetadata(
            document_id="integration_test_doc",
            metadata_id="integration_test_meta",
            title="ML Frameworks Guide",
            tags=["machine-learning", "python", "frameworks"]
        )

        self.document = Document(
            id="integration_test_doc",
            filename="ml_frameworks.md",
            file_path="/test/ml_frameworks.md",
            file_type=".md",
            file_size=len(self.test_content),
            title="ML Frameworks Guide",
            raw_content=self.test_content,
            clean_content=self.test_content,  # Assume already cleaned
            metadata=self.metadata,
            textChunks=[]
        )

    def test_document_level_kg_extraction_flow(self):
        """Test document-level KG extraction decision and processing"""
        # Document should be small enough for document-level processing
        assert self.document.should_use_document_level_kg() == True
        assert self.document.validate_content_for_kg() == True

        # Initialize KG extraction service
        kg_service = KGExtractionService(llm_provider="mock")  # Use mock for testing

        # Extract from document
        result = kg_service.extract_from_document(self.document)

        # Verify extraction results
        assert isinstance(result, dict)
        assert 'entities' in result
        assert 'relations' in result
        assert len(result['entities']) > 0
        assert len(result['relations']) > 0

        # Verify document was updated
        assert self.document.knowledge_graph is not None
        assert self.document.is_kg_extracted == True
        assert self.document.kg_extracted_at is not None
        assert self.document.kg_extraction_metadata is not None

    def test_chunk_level_kg_extraction_flow(self):
        """Test chunk-level KG extraction for large documents"""
        # Create large document that requires chunk-level processing
        large_content = self.test_content * 100  # Make it large
        large_document = Document(
            id="large_test_doc",
            filename="large_ml_guide.md",
            file_path="/test/large_ml_guide.md",
            file_type=".md",
            file_size=len(large_content),
            title="Large ML Frameworks Guide",
            raw_content=large_content,
            clean_content=large_content,
            metadata=self.metadata,
            textChunks=[],
            kg_extraction_token_limit=1000  # Set low limit to force chunk processing
        )

        # Document should require chunk-level processing
        assert large_document.should_use_document_level_kg() == False

        # Initialize KG extraction service
        kg_service = KGExtractionService(llm_provider="mock")

        # Simulate chunk processing
        chunks = [large_content[i:i+500] for i in range(0, len(large_content), 500)]
        result = kg_service.extract_from_chunks(chunks[:3], "large_test_doc")  # Test first 3 chunks

        # Verify chunk-level extraction results
        assert isinstance(result, dict)
        assert 'entities' in result
        assert 'relations' in result
        assert len(result['entities']) > 0

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_database_integration_flow(self, mock_sqlite_cls):
        """Test complete flow with database storage"""
        # Setup mock services
        mock_sqlite_service = MagicMock()
        mock_sqlite_cls.return_value = mock_sqlite_service
        mock_sqlite_service.save_document.return_value = True

        # Initialize database client (SQLite only for this test)
        db_config = {
            'sqlite': {'db_location': '/tmp/test_integration.db'}
        }
        db_client = DatabaseClient(db_config)

        # Initialize KG extraction service
        kg_service = KGExtractionService(llm_provider="mock")

        # Extract KG from document
        kg_result = kg_service.extract_from_document(self.document)

        # Save document to SQLite
        save_result = db_client.save_document(self.document)
        assert save_result == True

        # Verify mock was called
        mock_sqlite_service.save_document.assert_called_once_with(self.document)

        # Test KG-specific operations gracefully handle missing Neo4j
        kg_save_result = db_client.save_knowledge_graph("integration_test_doc", kg_result)
        assert kg_save_result == False  # Should fail gracefully when Neo4j not available

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_dual_database_integration_flow(self, mock_sqlite_cls):
        """Test complete flow with dual database storage (Neo4j graceful fallback)"""
        # Setup mock services
        mock_sqlite_service = MagicMock()
        mock_sqlite_cls.return_value = mock_sqlite_service
        mock_sqlite_service.save_document.return_value = True

        # Initialize database client with both databases (Neo4j will fail gracefully)
        db_config = {
            'sqlite': {'db_location': '/tmp/test_integration.db'},
            'neo4j': {
                'host': 'localhost',
                'port': 7687,
                'username': 'neo4j',
                'password': 'password',
                'database': 'test'
            }
        }
        db_client = DatabaseClient(db_config)

        # Initialize KG extraction service
        kg_service = KGExtractionService(llm_provider="mock")

        # Complete integration flow
        # 1. Extract KG from document
        kg_result = kg_service.extract_from_document(self.document)

        # 2. Save document to SQLite
        doc_save_result = db_client.save_document(self.document)
        assert doc_save_result == True

        # 3. Attempt to save KG to Neo4j (should fail gracefully)
        kg_save_result = db_client.save_knowledge_graph("integration_test_doc", kg_result)
        assert kg_save_result == False  # Should fail gracefully when Neo4j not available

        # 4. Verify SQLite service was called
        mock_sqlite_service.save_document.assert_called_once_with(self.document)

        # 5. Verify dual database client has both configurations but only SQLite works
        assert db_client.sqlite_service is not None
        assert db_client.neo4j_service is None  # Should be None due to connection failure

    def test_kg_extraction_context_generation(self):
        """Test that document context is properly generated for KG extraction"""
        context = self.document.get_kg_extraction_context()

        # Should include document title, type, and tags
        assert "ML Frameworks Guide" in context
        assert ".md" in context
        assert "machine-learning" in context

        # Initialize KG extraction service
        kg_service = KGExtractionService(llm_provider="mock")

        # Extract with context
        result = kg_service.extract_from_text(self.test_content, context=context)

        assert isinstance(result, dict)
        assert 'entities' in result
        assert 'relations' in result

    def test_extraction_metadata_and_performance_tracking(self):
        """Test that extraction metadata is properly tracked"""
        kg_service = KGExtractionService(llm_provider="mock")

        # Extract with metadata tracking
        result = kg_service.extract_from_document(self.document)

        # Check document metadata was updated
        assert self.document.kg_extraction_metadata is not None
        metadata = self.document.kg_extraction_metadata

        assert 'extraction_time' in metadata
        assert 'entity_count' in metadata
        assert 'relation_count' in metadata
        assert 'strategy_used' in metadata
        assert metadata['extraction_time'] > 0

    def test_error_handling_and_fallback_behavior(self):
        """Test error handling and graceful fallback in the pipeline"""
        # Test with invalid document content
        invalid_document = Document(
            id="invalid_doc",
            filename="empty.md",
            file_path="/test/empty.md",
            file_type=".md",
            file_size=0,
            title="Empty Document",
            raw_content="",
            clean_content="",
            metadata=self.metadata,
            textChunks=[]
        )

        # Should not be suitable for KG extraction
        assert invalid_document.validate_content_for_kg() == False

        # But service should handle it gracefully
        kg_service = KGExtractionService(llm_provider="mock")
        result = kg_service.extract_from_document(invalid_document)

        # Should return empty results
        assert result['entities'] == set()
        assert result['relations'] == []

        # Document should still be marked as processed
        assert invalid_document.is_kg_extracted == True

    def test_batch_processing_integration(self):
        """Test batch processing of multiple documents"""
        # Create multiple test documents
        documents = []
        for i in range(3):
            doc_dict = {
                'id': f'batch_doc_{i}',
                'text': f'Document {i}: {self.test_content}'
            }
            documents.append(doc_dict)

        # Initialize KG extraction service
        kg_service = KGExtractionService(llm_provider="mock")

        # Process batch
        results = kg_service.extract_batch(documents)

        # Verify batch results
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result['document_id'] == f'batch_doc_{i}'
            assert 'entities' in result
            assert 'relations' in result
            assert len(result['entities']) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])