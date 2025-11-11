"""Document dataclasses used across ingestion and services."""

from .citation import Citation
from .chunk import ChunkMetadata, TextChunk
from .metadata import DocumentMetadata
from .document import Document

__all__ = [
    "Citation",
    "ChunkMetadata",
    "TextChunk",
    "DocumentMetadata",
    "Document",
]

