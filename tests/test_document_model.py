import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.document.models.document import Document
from knowledge_graph.document.models.metadata import DocumentMetadata
from datetime import datetime

class TestDocumentModel:
    """Test enhanced Document model with KG fields and methods"""

    def setup_method(self):
        """Setup test environment"""
        self.sample_metadata = DocumentMetadata(
            document_id="test_doc_1",
            metadata_id="test_meta_1",
            title="Test Document",
            tags=["machine-learning", "python", "data-science"]
        )

    def create_test_document(self, content="Sample document content for testing."):
        """Helper to create test document"""
        return Document(
            id="test_doc_1",
            filename="test.md",
            file_path="/test/test.md",
            file_type=".md",
            file_size=len(content),
            title="Test Document",
            raw_content=content,
            clean_content=content,  # Assume cleaned
            metadata=self.sample_metadata,
            textChunks=[]
        )

    def test_new_kg_fields_initialization(self):
        """Test that new KG fields are properly initialized"""
        document = self.create_test_document()

        # Test KG fields default values
        assert document.knowledge_graph is None
        assert document.kg_extraction_metadata is None
        assert document.is_kg_extracted == False
        assert document.kg_extraction_token_limit == 8000
        assert document.kg_extraction_strategy == "auto"
        assert document.kg_extracted_at is None

        # Test wiki_links field
        assert document.wiki_links == []

    def test_token_counting(self):
        """Test token estimation accuracy"""
        # Test with known content
        short_content = "This is a test."  # ~15 chars = ~4 tokens
        long_content = "This is a much longer piece of content that should have more tokens. " * 10  # ~700 chars = ~175 tokens

        short_doc = self.create_test_document(short_content)
        long_doc = self.create_test_document(long_content)

        short_tokens = short_doc.estimate_token_count()
        long_tokens = long_doc.estimate_token_count()

        assert short_tokens > 0
        assert long_tokens > short_tokens
        assert short_tokens < 10  # Should be small
        assert long_tokens > 100  # Should be larger

    def test_document_level_decision_logic(self):
        """Test document vs chunk level extraction decision"""
        # Small document - should use document level
        small_content = "Short document content."
        small_doc = self.create_test_document(small_content)
        assert small_doc.should_use_document_level_kg() == True

        # Large document - should use chunk level
        large_content = "Very large document content. " * 1000  # ~30k chars = ~7.5k tokens
        large_doc = self.create_test_document(large_content)
        large_doc.kg_extraction_token_limit = 5000  # Set lower limit
        assert large_doc.should_use_document_level_kg() == False

    def test_content_validation(self):
        """Test content quality validation for KG extraction"""
        # Valid content
        good_content = "This is a good document with substantial content that discusses machine learning concepts and their applications in data science."
        good_doc = self.create_test_document(good_content)
        assert good_doc.validate_content_for_kg() == True

        # Too short content
        short_content = "Short."
        short_doc = self.create_test_document(short_content)
        assert short_doc.validate_content_for_kg() == False

        # Mostly code content
        code_content = """
This document is mostly code:

```python
def function_one():
    return "lots of code"

def function_two():
    return "more code"

class MyClass:
    def __init__(self):
        self.value = "even more code"

def function_three():
    return "tons of code here"
```

Just a tiny bit of text.
"""
        code_doc = self.create_test_document(code_content)
        assert code_doc.validate_content_for_kg() == False

    def test_kg_extraction_context_generation(self):
        """Test context string generation for kg-gen"""
        document = self.create_test_document()

        context = document.get_kg_extraction_context()

        assert "Document: Test Document" in context
        assert "Type: .md" in context
        assert "Tags: machine-learning" in context

    def test_empty_content_handling(self):
        """Test handling of empty or None content"""
        empty_doc = self.create_test_document("")

        assert empty_doc.estimate_token_count() == 0
        assert empty_doc.validate_content_for_kg() == False
        assert empty_doc.should_use_document_level_kg() == True  # 0 tokens < limit

    def test_custom_token_limit(self):
        """Test custom token limits"""
        content = "Medium sized content. " * 100  # ~2k chars = ~500 tokens
        document = self.create_test_document(content)

        # With high limit - should use document level
        document.kg_extraction_token_limit = 1000
        assert document.should_use_document_level_kg() == True

        # With low limit - should use chunk level
        document.kg_extraction_token_limit = 100
        assert document.should_use_document_level_kg() == False

    def test_kg_metadata_storage(self):
        """Test that KG metadata can be stored and retrieved"""
        document = self.create_test_document()

        # Set KG extraction results
        test_graph = {
            'entities': ['Python', 'Machine Learning'],
            'relations': [('Python', 'used_for', 'Machine Learning')]
        }

        test_metadata = {
            'extraction_time': 1.5,
            'strategy_used': 'document_level',
            'token_count': 500
        }

        document.knowledge_graph = test_graph
        document.kg_extraction_metadata = test_metadata
        document.is_kg_extracted = True
        document.kg_extracted_at = datetime.now()

        assert document.knowledge_graph == test_graph
        assert document.kg_extraction_metadata == test_metadata
        assert document.is_kg_extracted == True
        assert document.kg_extracted_at is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])