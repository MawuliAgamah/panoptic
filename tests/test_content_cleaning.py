import pytest
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.document.manager.document_manager import DocumentManager
from knowledge_graph.document.models.document import Document
from knowledge_graph.document.models.metadata import DocumentMetadata
from datetime import datetime

class TestContentCleaning:
    """Test content cleaning functionality for Obsidian markdown processing"""

    def setup_method(self):
        """Setup test environment"""
        self.document_manager = DocumentManager(llm_service=None)
        self.sample_metadata = DocumentMetadata(
            document_id="test_doc_1",
            metadata_id="test_meta_1",
            title="Test Document"
        )

    def create_test_document(self, raw_content):
        """Helper to create test document with raw content"""
        return Document(
            id="test_doc_1",
            filename="test.md",
            file_path="/test/test.md",
            file_type=".md",
            file_size=len(raw_content),
            title="Test Document",
            raw_content=raw_content,
            clean_content="",  # To be filled by cleaning
            metadata=self.sample_metadata,
            textChunks=[]
        )

    def test_wiki_links_extraction_and_cleaning(self):
        """Test that wiki links are extracted and stored, then cleaned from content"""
        raw_content = "This discusses [[Machine Learning]] and [[Data Science]]."
        expected_clean = "This discusses Machine Learning and Data Science."
        expected_links = ["Machine Learning", "Data Science"]

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == expected_clean
        assert hasattr(cleaned_document, 'wiki_links')
        assert cleaned_document.wiki_links == expected_links
        assert cleaned_document.is_preprocessed == True

    def test_embedded_files_removal(self):
        """Test that embedded files ![[file]] are removed"""
        raw_content = "Here's an image ![[screenshot.png]] and a file ![[document.pdf]]."
        expected = "Here's an image  and a file ."

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == expected

    def test_comment_removal(self):
        """Test that Obsidian comments %%text%% are removed"""
        raw_content = "This is visible %%this is a comment%% and this too."
        expected = "This is visible  and this too."

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == expected

    def test_markdown_formatting_removal(self):
        """Test that markdown formatting is cleaned"""
        raw_content = "This is **bold** and *italic* and `code`."
        expected = "This is bold and italic and code."

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == expected

    def test_header_removal(self):
        """Test that markdown headers are cleaned"""
        raw_content = """# Main Header
## Sub Header
### Sub Sub Header
Content here."""
        expected = """Main Header
Sub Header
Sub Sub Header
Content here."""

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == expected

    def test_whitespace_normalization(self):
        """Test that excessive whitespace is normalized"""
        raw_content = "Line one\n\n\n\n\nLine two\n\n\n\nLine three"
        expected = "Line one\n\nLine two\n\nLine three"

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == expected

    def test_complex_obsidian_note(self):
        """Test cleaning a complex Obsidian note with multiple features"""
        raw_content = """# My Learning Notes

This note discusses [[Machine Learning]] and its applications.

%%TODO: Add more examples%%

## Key Points

- **Important**: ML is used in [[Data Science]]
- *Also*: Check out this image ![[ml_diagram.png]]
- `python` is commonly used

### Code Example
```python
# This should be preserved
print("Hello World")
```

Final thoughts on [[Artificial Intelligence]].
"""

        expected_wiki_links = ["Machine Learning", "Data Science", "Artificial Intelligence"]

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        # Check wiki links extracted
        assert hasattr(cleaned_document, 'wiki_links')
        assert set(cleaned_document.wiki_links) == set(expected_wiki_links)

        # Check that unwanted syntax is removed
        assert "[[" not in cleaned_document.clean_content
        assert "]]" not in cleaned_document.clean_content
        assert "%%" not in cleaned_document.clean_content
        assert "![[" not in cleaned_document.clean_content

    def test_empty_content(self):
        """Test handling of empty or minimal content"""
        raw_content = ""

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == ""
        assert cleaned_document.wiki_links == []
        assert cleaned_document.is_preprocessed == True

    def test_no_wiki_links(self):
        """Test document with no wiki links"""
        raw_content = "This is just regular text with **formatting**."
        expected = "This is just regular text with formatting."

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        assert cleaned_document.clean_content == expected
        assert cleaned_document.wiki_links == []

    def test_preserves_code_blocks(self):
        """Test that code blocks are preserved"""
        raw_content = """Here's some code:

```python
def hello():
    return "world"
```

And more text."""

        document = self.create_test_document(raw_content)
        cleaned_document = self.document_manager.clean_document(document)

        # Code blocks should be preserved
        assert "def hello():" in cleaned_document.clean_content
        assert "return \"world\"" in cleaned_document.clean_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])