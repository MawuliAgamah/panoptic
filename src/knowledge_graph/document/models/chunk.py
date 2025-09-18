from dataclasses import dataclass, field
from typing import List, Dict, Optional

@dataclass
class ChunkMetadata:
    """Metadata specific to a text chunk"""

    # Position in document
    start_index: int             # Start position in original document
    end_index: int               # End position in original document
    
    # Structural context
    section_title: Optional[str] = None      # Title of the section containing chunk
    section_depth: int = 0                   # Heading level (1 for h1, 2 for h2, etc.)
    page_number: Optional[int] = None        # Page number in source document

    
    # Content analysis
    language: Optional[str] = None           # Language of this specific chunk
    word_count: int = 0                      # Number of words in chunk
    # reading_time: float = 0.0                # Estimated reading time in seconds
    # reading_level: Optional[str] = None      # Readability score/level
    
    # Semantic information
    topics: List[str] = field(default_factory=list, metadata={"max_items": 3})  # Main topics in chunk (max 3)
    keywords: List[str] = field(default_factory=list, metadata={"max_items": 3})  # Key terms (max 3)
    # importance_score: float = 0.0            # Relevance/importance within document
    
    # Processing metadata
    chunk_strategy: str = "paragraph"        # How chunk was created
    embedding_model: Optional[str] = None    # Model used for embedding

    

@dataclass
class TextChunk:
    """A discrete segment of document text"""
    id: str                      # Unique identifier
    document_id: str             # Reference to parent document
    content: str                 # Chunk text content
    metadata: ChunkMetadata      # Chunk-specific metadata
    
    
    # Content navigation
    #section: Optional[str] = None             # Document section
    #heading: Optional[str] = None             # Nearest heading
    #page_num: Optional[int] = None            # Page number
    previous_chunk_id: Optional[str] = None   # Previous chunk
    next_chunk_id: Optional[str] = None       # Next chunk
    
    # Semantic information
    embedding: Optional[List[float]] = None   # Vector embedding
    summary: Optional[str] = None             # Generated summary
    
    def __str__(self):
        return self.content