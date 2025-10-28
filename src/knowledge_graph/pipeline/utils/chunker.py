"""Chunking utilities used by the document processing pipeline."""

from __future__ import annotations

import re
from typing import Any, List, Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ...document.models.chunk import ChunkMetadata, TextChunk


class MarkdownSection:
    """Represents a section in a markdown document with hierarchical structure."""

    def __init__(self, level: int, title: str, content: str = "") -> None:
        self.level = level
        self.title = title
        self.content = content
        self.subsections: List["MarkdownSection"] = []
        self.parent: Optional["MarkdownSection"] = None
        self.start_index = 0
        self.end_index = 0

    def add_subsection(self, section: "MarkdownSection") -> None:
        section.parent = self
        self.subsections.append(section)

    def full_content(self, include_headers: bool = True) -> str:
        result = ""
        if include_headers and self.title:
            result += ("#" * self.level) + " " + self.title + "\n\n"
        result += self.content
        for subsection in self.subsections:
            result += subsection.full_content(include_headers)
        return result

    def size(self) -> int:
        return len(self.full_content())

    def get_full_path(self) -> str:
        if self.parent is None:
            return self.title
        return self.parent.get_full_path() + " > " + self.title

    def __str__(self) -> str:
        return (
            f"Section(level={self.level}, title='{self.title}', "
            f"size={self.size()}, subsections={len(self.subsections)})"
        )


class StructuredMarkdownChunker:
    """Chunks markdown text by respecting the document's header structure."""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, max_depth: int = 4) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_depth = max_depth
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def parse_document(self, text: str) -> List[MarkdownSection]:
        header_pattern = re.compile(r"^(#{1,6})\s+(.+?)(?:\s+#+)?$", re.MULTILINE)
        headers = [(len(match.group(1)), match.group(2).strip(), match.start()) for match in header_pattern.finditer(text)]
        headers.append((0, "", len(text)))

        root_sections: List[MarkdownSection] = []
        section_stack: List[MarkdownSection] = []

        for i in range(len(headers) - 1):
            level, title, start = headers[i]
            next_start = headers[i + 1][2]

            if level > self.max_depth:
                continue

            content_start = start + len("#" * level) + len(title) + 2
            content = text[content_start:next_start].strip()

            content_lines = content.split("\n")
            if content_lines and content_lines[0].strip() == "":
                content = "\n".join(content_lines[1:])

            section = MarkdownSection(level, title, content)
            section.start_index = start
            section.end_index = next_start

            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()

            if not section_stack:
                root_sections.append(section)
            else:
                section_stack[-1].add_subsection(section)

            section_stack.append(section)

        return root_sections

    def chunk_section(self, section: MarkdownSection, max_size: int, depth: int = 1) -> List[str]:
        chunks: List[str] = []

        if section.size() <= max_size:
            chunks.append(section.full_content())
            return chunks

        if depth >= self.max_depth or not section.subsections:
            context = ""
            current = section
            while current:
                if current.title:
                    prefix = "#" * current.level + " "
                    context = prefix + current.title + "\n\n" + context
                current = current.parent

            full_text = context + section.content
            chunks.extend(self.fallback_splitter.split_text(full_text))
            return chunks

        current_chunk = ""
        section_header = ("#" * section.level) + " " + section.title + "\n\n" if section.title else ""

        if section.content:
            current_chunk = section_header + section.content
        else:
            current_chunk = section_header

        for subsection in section.subsections:
            subsection_size = subsection.size()

            if subsection_size > max_size:
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                chunks.extend(self.chunk_section(subsection, max_size, depth + 1))
            elif len(current_chunk) + subsection_size > max_size:
                chunks.append(current_chunk)
                current_chunk = section_header + subsection.full_content()
            else:
                current_chunk += subsection.full_content()

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def chunk_document(self, document: Any) -> List[str]:
        print(f"Chunking document {document.id} using StructuredMarkdownChunker")

        if not document.raw_content:
            print("Warning: Document has no content to chunk")
            return []

        root_sections = self.parse_document(document.raw_content)
        print(f"Found {len(root_sections)} root sections in document")

        chunks: List[str] = []
        for section in root_sections:
            chunks.extend(self.chunk_section(section, self.chunk_size))

        print(f"Created {len(chunks)} chunks")
        return chunks

    def create_chunk_metadata(self, document: Any, chunks: List[str]) -> List[ChunkMetadata]:
        print("Creating metadata for chunks")

        chunk_metadatas: List[ChunkMetadata] = []
        current_position = 0

        for chunk_text in chunks:
            word_count = len(chunk_text.split())

            start_index = document.raw_content.find(chunk_text, current_position)
            if start_index == -1:
                start_index = document.raw_content.find(chunk_text)
            end_index = start_index + len(chunk_text) if start_index != -1 else -1

            current_position = end_index if end_index != -1 else current_position

            metadata = ChunkMetadata(
                start_index=start_index,
                end_index=end_index,
                word_count=word_count,
                language=getattr(document.metadata, "language", "en"),
            )
            chunk_metadatas.append(metadata)

        return chunk_metadatas

    def reconstruct_document(self, document: Any, chunks: List[str], chunk_metadatas: List[ChunkMetadata]) -> List[TextChunk]:
        text_chunks: List[TextChunk] = []

        for i, (chunk_text, metadata) in enumerate(zip(chunks, chunk_metadatas)):
            chunk_id = f"{document.id}_chunk_{i}"
            prev_id = f"{document.id}_chunk_{i-1}" if i > 0 else None
            next_id = f"{document.id}_chunk_{i+1}" if i < len(chunks) - 1 else None

            chunk = TextChunk(
                id=chunk_id,
                document_id=document.id,
                content=chunk_text,
                metadata=metadata,
                previous_chunk_id=prev_id,
                next_chunk_id=next_id,
            )
            text_chunks.append(chunk)

        print(f"Created {len(text_chunks)} text chunks")
        return text_chunks


class Chunker:
    """Handles document chunking with various strategies."""

    def __init__(self, chunk_size: int = 2000, chunk_overlap: int = 200, chunker_type: str = "auto") -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker_type = chunker_type

        self.recursive_character_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        self.structured_markdown_chunker = StructuredMarkdownChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_depth=4,
        )

    def chunk_document(self, document) -> List[str]:
        if not document.raw_content:
            print("Warning: Document has no content to chunk")
            return []

        use_markdown_chunker = self.chunker_type == "structured_markdown"

        if self.chunker_type == "auto":
            if hasattr(document, "file_type") and document.file_type.lower() in [".md", ".markdown"]:
                use_markdown_chunker = True
            elif re.search(r"^#{1,6}\s+.+$", document.raw_content, re.MULTILINE):
                use_markdown_chunker = True

        if use_markdown_chunker:
            print(f"Chunking document {document.id} using structured markdown chunker")
            return self.structured_markdown_chunker.chunk_document(document)

        print(f"Chunking document {document.id} using standard recursive chunker")
        doc_chunks = self.recursive_character_splitter.split_text(document.raw_content)
        return [chunk.page_content if isinstance(chunk, Document) else chunk for chunk in doc_chunks]

    def create_chunk_metadata(self, document, chunks: List[str]) -> List[ChunkMetadata]:
        return self.structured_markdown_chunker.create_chunk_metadata(document, chunks)

    def reconstruct_document(self, document, chunks: List[str], chunk_metadatas: List[ChunkMetadata]) -> List[TextChunk]:
        return self.structured_markdown_chunker.reconstruct_document(document, chunks, chunk_metadatas)
