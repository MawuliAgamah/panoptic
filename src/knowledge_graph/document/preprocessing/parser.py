from abc import ABC, abstractmethod
from typing import Dict, Type
import os

class DocumentParser(ABC):
    """Base class for document parsers."""
    
    @abstractmethod
    def parse(self, file_path: str) -> str:
        """
        Parse document and extract content.
        
        Args:
            file_path: Path to the document
            
        Returns:
            str: Document content
        """
        pass


class DefaultParser(DocumentParser):
    """Default parser for unknown file types."""
    def parse(self, file_path: str) -> str:
        """Parse an unknown file type."""
        print(f"Using default parser for {file_path}")
        return ""  # Return empty string for unsupported file types


class TextParser(DocumentParser):
    """Parser for plain text files."""
    def parse(self, file_path: str) -> str:
        """Parse a text file and return content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            print(f"Text file parsed: {len(content)} chars")
            return content
        
        except Exception as e:
            print(f"Error parsing text file {file_path}: {str(e)}")
            return ""


class MarkdownParser(DocumentParser):
    """Parser for Markdown files."""
    
    def parse(self, file_path: str) -> str:
        """Parse a markdown file and return content."""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            print(f"Markdown file parsed: {len(content)} chars")
            return content
            
        except Exception as e:
            print(f"Error parsing markdown file {file_path}: {str(e)}")
            return ""


def _get_parser_for_type(file_type):
    """
    Get appropriate parser for file type.
    
    This is maintained for backward compatibility with existing code.
    New code should use ParserFactory directly.
    """
    parsers = {
        '.md': MarkdownParser(),
        'markdown': MarkdownParser(),
        'txt': TextParser(),
        'text': TextParser()
    }
    return parsers.get(file_type.lower() if file_type else '', DefaultParser())


class ParserFactory:
    """Factory for creating document parsers based on document type."""
    
    _parsers: Dict[str, Type[DocumentParser]] = {
        'markdown': MarkdownParser,
        'md': MarkdownParser,
        '.md': MarkdownParser,
        'txt': TextParser,
        'text': TextParser,
    }
    
    @classmethod
    def get_parser(cls, document_type: str) -> DocumentParser:
        """Get appropriate parser for document type"""
        doc_type = document_type.lower() if document_type else 'text'
        parser_class = cls._parsers.get(doc_type)
        
        if not parser_class:
            print(f"No parser found for {document_type}, using default parser")
            parser_class = DefaultParser
            
        return parser_class()
    
    @classmethod
    def register_parser(cls, document_type: str, parser_class: Type[DocumentParser]):
        """Register a new parser for a document type"""
        cls._parsers[document_type.lower()] = parser_class