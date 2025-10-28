"""Document parsing utilities used by the processing pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Type


class DocumentParser(ABC):
    """Base class for document parsers."""

    @abstractmethod
    def parse(self, file_path: str) -> str:
        """Parse document and extract raw content."""
        raise NotImplementedError


class DefaultParser(DocumentParser):
    """Default parser for unknown file types."""

    def parse(self, file_path: str) -> str:
        """Return empty content for unsupported types."""
        print(f"Using default parser for {file_path}")
        return ""


class TextParser(DocumentParser):
    """Parser for plain text files."""

    def parse(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            print(f"Text file parsed: {len(content)} chars")
            return content
        except Exception as exc:
            print(f"Error parsing text file {file_path}: {exc}")
            return ""


class MarkdownParser(DocumentParser):
    """Parser for Markdown files."""

    def parse(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            print(f"Markdown file parsed: {len(content)} chars")
            return content
        except Exception as exc:
            print(f"Error parsing markdown file {file_path}: {exc}")
            return ""


class ParserFactory:
    """Factory for creating document parsers based on document type."""

    _parsers: Dict[str, Type[DocumentParser]] = {
        "markdown": MarkdownParser,
        "md": MarkdownParser,
        ".md": MarkdownParser,
        "txt": TextParser,
        "text": TextParser,
    }

    @classmethod
    def get_parser(cls, document_type: str) -> DocumentParser:
        """Return a parser instance for the supplied type."""
        doc_type = document_type.lower() if document_type else "text"
        parser_class = cls._parsers.get(doc_type)

        if not parser_class:
            print(f"No parser found for {document_type}, using default parser")
            parser_class = DefaultParser

        return parser_class()

    @classmethod
    def register_parser(cls, document_type: str, parser_class: Type[DocumentParser]) -> None:
        """Register a new parser class for the given type."""
        cls._parsers[document_type.lower()] = parser_class
