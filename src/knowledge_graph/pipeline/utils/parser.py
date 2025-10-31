"""Document parsing utilities used by the processing pipeline."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Type
import logging

try:  # Optional dependency for PDF parsing
    import PyPDF2  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    PyPDF2 = None

try:  # Optional dependency for DOCX parsing
    import docx  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    docx = None

logger = logging.getLogger("knowledgeAgent.pipeline.parser")


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
        logger.warning("Using default parser for unsupported file: %s", file_path)
        return ""


class TextParser(DocumentParser):
    """Parser for plain text files."""

    def parse(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            logger.debug("Parsed text file %s: %d chars", file_path, len(content))
            return content
        except Exception as exc:
            logger.error("Error parsing text file %s: %s", file_path, exc)
            return ""


class MarkdownParser(DocumentParser):
    """Parser for Markdown files."""

    def parse(self, file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                content = file.read()
            logger.debug("Parsed markdown file %s: %d chars", file_path, len(content))
            return content
        except Exception as exc:
            logger.error("Error parsing markdown file %s: %s", file_path, exc)
            return ""

class DocxParser(DocumentParser):
    """Parser for Microsoft Word .docx files using python-docx."""

    def parse(self, file_path: str) -> str:
        if docx is None:  # pragma: no cover - optional
            logger.warning("python-docx not installed; cannot parse DOCX: %s", file_path)
            return ""
        try:
            document = docx.Document(file_path)
            paragraphs = [p.text for p in document.paragraphs]
            content = "\n".join(p for p in paragraphs if p is not None)
            logger.debug("Parsed DOCX file %s: %d chars", file_path, len(content))
            return content
        except Exception as exc:
            logger.error("Error parsing DOCX file %s: %s", file_path, exc)
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

    if PyPDF2 is not None:
        class PDFParser(DocumentParser):
            """Parser for PDF documents using PyPDF2."""

            def parse(self, file_path: str) -> str:
                try:
                    with open(file_path, "rb") as pdf_file:
                        reader = PyPDF2.PdfReader(pdf_file)
                        pages = [page.extract_text() or "" for page in reader.pages]
                    logger.debug("Parsed PDF file %s: %d pages", file_path, len(pages))
                    return "\n".join(pages)
                except Exception as exc:  # pragma: no cover - depends on PyPDF2 internals
                    logger.error("Error parsing PDF file %s: %s", file_path, exc)
                    return ""

        _parsers.update({
            "pdf": PDFParser,
            ".pdf": PDFParser,
        })

    # Register DOCX parser if available
    if docx is not None:
        _parsers.update({
            "docx": DocxParser,
            ".docx": DocxParser,
            "doc": DocxParser,
            ".doc": DocxParser,
        })

    @classmethod
    def get_parser(cls, document_type: str) -> DocumentParser:
        """Return a parser instance for the supplied type."""
        doc_type = document_type.lower() if document_type else "text"
        parser_class = cls._parsers.get(doc_type)

        if not parser_class:
            logger.info("No specific parser for '%s'; using default parser", document_type)
            parser_class = DefaultParser

        return parser_class()

    @classmethod
    def register_parser(cls, document_type: str, parser_class: Type[DocumentParser]) -> None:
        """Register a new parser class for the given type."""
        cls._parsers[document_type.lower()] = parser_class
