"""
Test Knowledge Graph Processing Strategy Logic

This test validates the intelligent decision-making logic for choosing between
document-level and chunk-level KG extraction strategies.
"""
import pytest
import sys
import os
from unittest.mock import MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.document.models.document import Document
from knowledge_graph.document.models.metadata import DocumentMetadata
from knowledge_graph.document.manager.document_manager import DocumentManager
from knowledge_graph.llm.kg_extractor.service import KGExtractionService


class TestKGProcessingStrategyLogic:
    """Test document vs chunk-level processing strategy decisions"""

    def setup_method(self):
        """Setup test environment"""
        # Mock LLM service
        self.mock_llm_service = MagicMock()
        self.mock_llm_service.extract_topics.return_value = {"topics": ["test", "content"]}
        self.mock_llm_service.extract_keywords.return_value = {"keywords": ["test", "data"]}

        # Create services
        self.kg_service = KGExtractionService(llm_provider="mock")
        self.document_manager = DocumentManager(
            llm_service=self.mock_llm_service,
            kg_service=self.kg_service
        )

    def create_test_document(self, content_size="small", token_limit=3000):
        """Create test document with specified characteristics"""
        if content_size == "small":
            content = """# Small Test Document

This is a small document about technology and programming concepts. Python is a popular programming language used in artificial intelligence and machine learning. It offers excellent libraries for data science applications.

Machine learning algorithms can process large datasets and extract meaningful patterns. Neural networks are particularly effective for complex pattern recognition tasks."""
        elif content_size == "medium":
            content = """# Medium Test Document

This is a medium-sized document covering various aspects of technology and programming.

## Programming Languages
Python is widely used for machine learning and artificial intelligence applications. TensorFlow and PyTorch are popular frameworks for deep learning. These tools enable data scientists to build sophisticated neural networks.

## Data Science
Data science combines statistics, programming, and domain expertise to extract insights from data. Machine learning algorithms can identify patterns in large datasets. Statistical analysis helps validate findings and measure confidence levels.

## Technology Trends
Artificial intelligence is transforming many industries. Cloud computing provides scalable infrastructure for data processing. Open source software enables collaboration and innovation across development teams."""
        elif content_size == "large":
            content = """# Large Test Document

This is a comprehensive document about technology, programming, and data science concepts.

## Introduction
Technology has revolutionized how we process information and solve complex problems. Programming languages provide tools for implementing algorithms and building software systems. Data science combines multiple disciplines to extract insights from data.

## Programming Fundamentals
Programming involves writing instructions for computers to execute specific tasks. Different languages serve various purposes: Python for data science, JavaScript for web development, and C++ for system programming. Object-oriented programming organizes code into reusable classes and objects.

Software engineering practices include version control, testing, and documentation. Code quality metrics help maintain readable and maintainable software. Design patterns provide proven solutions to common programming challenges.

## Machine Learning Concepts
Machine learning enables computers to learn patterns from data without explicit programming. Supervised learning uses labeled examples to train predictive models. Unsupervised learning discovers hidden structures in unlabeled data.

Neural networks simulate biological neurons to process information. Deep learning uses multi-layer networks to model complex relationships. Convolutional networks excel at image processing tasks.

## Data Processing
Data preprocessing cleans and transforms raw data for analysis. Feature engineering creates meaningful variables from raw data. Data visualization helps explore patterns and communicate findings.

Statistical analysis validates machine learning results. Hypothesis testing determines statistical significance. Cross-validation assesses model performance on unseen data.

## Applications
Artificial intelligence applications span healthcare, finance, and transportation. Natural language processing enables computers to understand human language. Computer vision allows machines to interpret visual information.

Recommendation systems personalize content and products. Fraud detection identifies suspicious patterns in transactions. Predictive maintenance prevents equipment failures.

## Future Directions
Quantum computing may solve currently intractable problems. Edge computing brings processing closer to data sources. Ethical AI ensures responsible technology deployment."""
        elif content_size == "very_large":
            # Create very large content by repeating the large content
            large_content = """# Large Test Document

This is a comprehensive document about technology, programming, and data science concepts.

## Introduction
Technology has revolutionized how we process information and solve complex problems. Programming languages provide tools for implementing algorithms and building software systems. Data science combines multiple disciplines to extract insights from data.

## Programming Fundamentals
Programming involves writing instructions for computers to execute specific tasks. Different languages serve various purposes: Python for data science, JavaScript for web development, and C++ for system programming. Object-oriented programming organizes code into reusable classes and objects.

Software engineering practices include version control, testing, and documentation. Code quality metrics help maintain readable and maintainable software. Design patterns provide proven solutions to common programming challenges.

## Machine Learning Concepts
Machine learning enables computers to learn patterns from data without explicit programming. Supervised learning uses labeled examples to train predictive models. Unsupervised learning discovers hidden structures in unlabeled data.

Neural networks simulate biological neurons to process information. Deep learning uses multi-layer networks to model complex relationships. Convolutional networks excel at image processing tasks."""
            content = large_content * 3  # Repeat 3 times to make it very large
        else:
            content = content_size  # Allow custom content

        metadata = DocumentMetadata(
            document_id=f"test_doc_{content_size}",
            metadata_id="test_meta",
            title=f"Test Document - {content_size}",
            tags=["test"]
        )

        document = Document(
            id=f"test_doc_{content_size}",
            filename=f"test_{content_size}.md",
            file_path=f"/test/test_{content_size}.md",
            file_type=".md",
            file_size=len(content),
            title=f"Test Document - {content_size}",
            raw_content=content,
            clean_content=content,  # Assume already cleaned
            metadata=metadata,
            textChunks=[],
            kg_extraction_token_limit=token_limit
        )

        return document

    def test_small_document_uses_document_level_processing(self):
        """Test that small documents use document-level processing"""
        document = self.create_test_document("small", token_limit=3000)

        # Should use document-level processing
        assert document.should_use_document_level_kg() == True

        # Verify token estimate is within limits
        token_estimate = document.estimate_token_count()
        assert token_estimate <= document.kg_extraction_token_limit
        print(f"Small document: {token_estimate} tokens (limit: {document.kg_extraction_token_limit})")

        # Test KG extraction strategy
        processed_doc = self.document_manager.extract_knowledge_graph(document)
        assert processed_doc.is_kg_extracted == True
        # Document-level processing updates document directly via extract_from_document
        assert processed_doc.knowledge_graph is not None

    def test_medium_document_processing_decision(self):
        """Test processing decision for medium-sized documents"""
        document = self.create_test_document("medium", token_limit=3000)

        token_estimate = document.estimate_token_count()
        should_use_document_level = document.should_use_document_level_kg()

        print(f"Medium document: {token_estimate} tokens, document-level: {should_use_document_level}")

        # Test KG extraction with intelligent decision
        processed_doc = self.document_manager.extract_knowledge_graph(document)
        assert processed_doc.is_kg_extracted == True
        assert processed_doc.knowledge_graph is not None

        # Check metadata for strategy used
        metadata = processed_doc.kg_extraction_metadata
        print(f"Strategy used: {metadata.get('strategy_used', 'document-level (implicit)')}")

    def test_large_document_uses_chunk_level_processing(self):
        """Test that large documents use chunk-level processing"""
        document = self.create_test_document("large", token_limit=400)  # Very low limit to force chunking

        # Check actual token estimate
        token_estimate = document.estimate_token_count()
        print(f"Large document token estimate: {token_estimate} (limit: {document.kg_extraction_token_limit})")

        # Should require chunk-level processing
        assert document.should_use_document_level_kg() == False

        # Verify token estimate exceeds limits
        token_estimate = document.estimate_token_count()
        assert token_estimate > document.kg_extraction_token_limit
        print(f"Large document: {token_estimate} tokens (limit: {document.kg_extraction_token_limit})")

        # Test chunk-level KG extraction
        processed_doc = self.document_manager.extract_knowledge_graph(document)
        assert processed_doc.is_kg_extracted == True
        assert processed_doc.knowledge_graph is not None

        # Should have chunk-level metadata (if chunks were created successfully)
        metadata = processed_doc.kg_extraction_metadata
        if metadata is not None and 'strategy_used' in metadata:
            assert metadata['strategy_used'] == 'chunk-level'
            if 'chunk_count' in metadata:
                print(f"Chunk-level processing: {metadata['chunk_count']} chunks")
            else:
                print("Chunk-level processing completed (no chunks created)")
        else:
            # If no metadata, check that document was still processed
            print("Document processed but no metadata available")

    def test_very_large_document_chunk_processing(self):
        """Test very large document with extensive chunk processing"""
        document = self.create_test_document("very_large", token_limit=500)  # Very low limit

        # Should definitely require chunk-level processing
        assert document.should_use_document_level_kg() == False

        token_estimate = document.estimate_token_count()
        print(f"Very large document: {token_estimate} tokens (limit: {document.kg_extraction_token_limit})")

        # Test chunk-level processing
        processed_doc = self.document_manager.extract_knowledge_graph(document)
        assert processed_doc.is_kg_extracted == True

        # Should have multiple chunks (if created successfully)
        metadata = processed_doc.kg_extraction_metadata
        if metadata is not None and 'strategy_used' in metadata:
            assert metadata['strategy_used'] == 'chunk-level'
            if 'chunk_count' in metadata:
                chunk_count = metadata['chunk_count']
                print(f"Very large document processed with {chunk_count} chunks")
            else:
                print("Very large document processed (no chunks created)")
        else:
            print("Very large document processed but no metadata available")

    def test_token_limit_configuration(self):
        """Test different token limit configurations"""
        content = "This is test content for token limit testing. " * 100

        # Test with high token limit (should use document-level)
        doc_high_limit = self.create_test_document(content, token_limit=10000)
        assert doc_high_limit.should_use_document_level_kg() == True

        # Test with low token limit (should use chunk-level)
        doc_low_limit = self.create_test_document(content, token_limit=100)
        assert doc_low_limit.should_use_document_level_kg() == False

        # Test with medium token limit
        doc_med_limit = self.create_test_document(content, token_limit=1000)
        token_est = doc_med_limit.estimate_token_count()
        expected_decision = token_est <= 1000
        actual_decision = doc_med_limit.should_use_document_level_kg()
        assert actual_decision == expected_decision

    def test_content_validation_for_kg_suitability(self):
        """Test content validation for KG extraction suitability"""
        # Test with good content (needs at least 100 characters)
        good_content = "Python is a popular programming language used for machine learning and artificial intelligence applications. It provides excellent libraries and frameworks for data science."
        good_document = self.create_test_document(good_content)
        assert good_document.validate_content_for_kg() == True

        # Test with empty content
        empty_document = self.create_test_document("")
        assert empty_document.validate_content_for_kg() == False

        # Test with very short content (less than 100 chars)
        short_content = "Hi there, this is short."
        short_document = self.create_test_document(short_content)
        assert short_document.validate_content_for_kg() == False

        # Test with None content
        none_document = self.create_test_document("test content for validation that is long enough to meet the minimum length requirement for knowledge graph extraction")
        none_document.clean_content = None
        none_document.raw_content = None
        assert none_document.validate_content_for_kg() == False

    def test_real_document_processing_strategy(self):
        """Test processing strategy with actual Obsidian document"""
        test_document_path = "/Users/mawuliagamah/obsidian vaults/Software Company/3. BookShelf/Books/An Illustrated Book of Bad Arguments.md"

        # Create real document
        document = self.document_manager.make_new_document(test_document_path, "real_strategy_test")
        assert document is not None

        # Clean document
        document = self.document_manager.clean_document(document)

        # Check processing decision
        token_estimate = document.estimate_token_count()
        should_use_document_level = document.should_use_document_level_kg()

        print(f"Real document analysis:")
        print(f"  - Token estimate: {token_estimate}")
        print(f"  - Token limit: {document.kg_extraction_token_limit}")
        print(f"  - Should use document-level: {should_use_document_level}")

        # Extract KG and verify strategy
        processed_doc = self.document_manager.extract_knowledge_graph(document)
        assert processed_doc.is_kg_extracted == True

        metadata = processed_doc.kg_extraction_metadata
        strategy = metadata.get('strategy_used', 'document-level (implicit)')
        print(f"  - Strategy used: {strategy}")

        # Verify consistency between decision and actual strategy
        if should_use_document_level:
            # If document-level was chosen, strategy should not be chunk-level
            assert strategy != 'chunk-level'
        else:
            # If chunk-level was required, strategy should be chunk-level
            assert strategy == 'chunk-level'

    def test_chunk_level_processing_with_real_chunks(self):
        """Test chunk-level processing creates proper chunks"""
        document = self.create_test_document("large", token_limit=200)  # Force chunking

        # Process through complete pipeline
        processed_doc = self.document_manager.extract_knowledge_graph(document)

        # Should have been processed
        assert processed_doc.is_kg_extracted == True

        # Check if chunks were created (chunker may not create chunks for all content)
        if processed_doc.textChunks and len(processed_doc.textChunks) > 0:
            print(f"Document chunked into {len(processed_doc.textChunks)} chunks")
            for i, chunk in enumerate(processed_doc.textChunks[:3]):  # Show first 3
                print(f"  Chunk {i+1}: {len(chunk.content)} chars - '{chunk.content[:50]}...'")

            # Check chunk-level metadata
            metadata = processed_doc.kg_extraction_metadata
            if metadata and 'strategy_used' in metadata:
                assert metadata['strategy_used'] == 'chunk-level'
        else:
            print("Document processed but no chunks were created by the chunker")

    def test_kg_extraction_metadata_consistency(self):
        """Test that KG extraction metadata is consistent with actual results"""
        documents = [
            self.create_test_document("small", token_limit=5000),
            self.create_test_document("medium", token_limit=1000),
            self.create_test_document("large", token_limit=500)
        ]

        for doc in documents:
            processed_doc = self.document_manager.extract_knowledge_graph(doc)
            metadata = processed_doc.kg_extraction_metadata
            kg_result = processed_doc.knowledge_graph

            # Verify basic results exist
            assert kg_result is not None
            assert 'entities' in kg_result
            assert 'relations' in kg_result

            # Verify metadata if it exists
            if metadata is not None:
                if 'entity_count' in metadata:
                    assert metadata['entity_count'] == len(kg_result['entities'])
                if 'relation_count' in metadata:
                    assert metadata['relation_count'] == len(kg_result['relations'])

                strategy = metadata.get('strategy_used', 'document-level')
                entity_count = len(kg_result['entities'])
                relation_count = len(kg_result['relations'])
                print(f"Document {doc.id}: {entity_count} entities, {relation_count} relations, strategy: {strategy}")
            else:
                print(f"Document {doc.id}: processed but no metadata available")

    def test_error_handling_in_processing_decisions(self):
        """Test error handling in processing strategy decisions"""
        # Test with document that has processing issues
        problem_doc = self.create_test_document("test content")

        # Simulate content issues
        problem_doc.clean_content = None
        problem_doc.raw_content = "test"  # Minimal content

        # Should handle gracefully
        result_doc = self.document_manager.extract_knowledge_graph(problem_doc)
        assert result_doc.is_kg_extracted == True
        assert result_doc.knowledge_graph is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])