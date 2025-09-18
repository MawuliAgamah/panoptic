from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime
from .citation import Citation
from .chunk import TextChunk
from .metadata import DocumentMetadata
from rich.console import Console

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
    
    # Processing information
    document_created_at: datetime = field(default_factory=datetime.now)
    preprocessed_at: Optional[datetime] = None
    
    # Storage information
    cache_location: Optional[str] = None
    is_cached: bool = False
    cache_created_at: Optional[datetime] = None
    cache_updated_at: Optional[datetime] = None
    is_preprocessed: bool = False
    is_chunked: bool = False
    is_metadata_generated: bool = False
    is_hash_generated: bool = False
    
