from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from .citation import Citation
from .chunk import TextChunk
from .metadata import DocumentMetadata

@dataclass
class Document:
    """Core representation of a preprocessed document."""
    id: str                      # Unique identifier
    filename: str                # Original filename
    file_path: str               # Original file path
    file_type: str               # File format (PDF, DOCX, MD, etc.)
    file_size: int               # Size in bytes
    title: str
    
    # Content
    raw_content: str             # Original extracted text
    clean_content: str           # Normalized/cleaned text
    
    # Metadata
    metadata: DocumentMetadata   # Extracted metadata
    
    # Chunks placeholder - will be filled during preprocessing
    textChunks: List[TextChunk]

    # Page-level content (primarily for PDFs)
    pages: List[str] = field(default_factory=list)

    # Obsidian-specific content
    wiki_links: List[str] = field(default_factory=list)  # Extracted [[links]]

    # Knowledge Graph fields
    knowledge_graph: Optional[Dict[str, Any]] = None  # kg-gen extracted graph
    kg_extraction_metadata: Optional[Dict[str, Any]] = None  # Extraction stats
    is_kg_extracted: bool = False  # KG extraction completed
    kg_extraction_token_limit: int = 8000  # Configurable threshold
    kg_extraction_strategy: str = "auto"  # "document", "chunk", or "auto"

    # Processing information
    document_created_at: datetime = field(default_factory=datetime.now)
    preprocessed_at: Optional[datetime] = None
    kg_extracted_at: Optional[datetime] = None
    
    # Storage information
    cache_location: Optional[str] = None
    is_cached: bool = False
    cache_created_at: Optional[datetime] = None
    cache_updated_at: Optional[datetime] = None
    is_preprocessed: bool = False
    is_chunked: bool = False
    is_metadata_generated: bool = False
    is_hash_generated: bool = False

    def estimate_token_count(self, text: Optional[str] = None) -> int:
        """Rough estimate of tokens for LLM processing"""
        content = text or self.clean_content or self.raw_content
        if not content:
            return 0
        # Approximate: 1 token ≈ 4 characters for English
        return len(content) // 4

    def should_use_document_level_kg(self) -> bool:
        """Determine if document is small enough for full document processing"""
        token_estimate = self.estimate_token_count()
        return token_estimate < self.kg_extraction_token_limit

    def validate_content_for_kg(self) -> bool:
        """Check if document content is suitable for KG extraction"""
        content = self.clean_content or self.raw_content

        if not content or len(content.strip()) < 100:
            return False

        # Skip content that's mostly code blocks (>70% code)
        import re
        code_blocks = re.findall(r'```.*?```', content, re.DOTALL)
        if code_blocks:
            code_length = sum(len(block) for block in code_blocks)
            code_ratio = code_length / len(content)
            if code_ratio > 0.7:
                return False

        return True

    def get_kg_extraction_context(self) -> str:
        """Generate context string for kg-gen processing"""
        context_parts = []

        if self.title:
            context_parts.append(f"Document: {self.title}")

        if self.file_type:
            context_parts.append(f"Type: {self.file_type}")

        if self.metadata and hasattr(self.metadata, 'tags') and self.metadata.tags:
            context_parts.append(f"Tags: {', '.join(self.metadata.tags[:3])}")

        return " | ".join(context_parts) if context_parts else "Personal knowledge document"

