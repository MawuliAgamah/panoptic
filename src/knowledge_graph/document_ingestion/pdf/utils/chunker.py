"""Chunking utilities used by the document processing pipeline."""

from __future__ import annotations

import re
from typing import Any, List, Optional
import logging

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from ....data_structs.document import ChunkMetadata, TextChunk

logger = logging.getLogger("knowledgeAgent.pipeline.chunk")


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
        logger.info("StructuredMarkdownChunker running for %s", document.id)

        if not document.raw_content:
            logger.warning("Document %s has no content to chunk", document.id)
            return []

        root_sections = self.parse_document(document.raw_content)

        def _count_sections(sections: List[MarkdownSection]) -> int:
            total = 0
            for s in sections:
                total += 1 + _count_sections(s.subsections)
            return total

        total_sections = _count_sections(root_sections)
        logger.info(
            "%s: detected %d root sections, %d total sections",
            document.id,
            len(root_sections),
            total_sections,
        )

        chunks: List[str] = []
        for section in root_sections:
            chunks.extend(self.chunk_section(section, self.chunk_size))

        if chunks:
            sizes = [len(c) for c in chunks]
            avg_sz = sum(sizes) // len(sizes)
            logger.info("%s: created %d chunks (avg=%d)", document.id, len(chunks), avg_sz)
            preview = (chunks[0][:200]).replace("\n", " ")
            logger.debug("%s: first chunk preview: '%s'%s", document.id, preview, "…" if len(preview) == 200 else "")
        else:
            logger.info("%s: created 0 chunks", document.id)
        return chunks

    def create_chunk_metadata(self, document: Any, chunks: List[str]) -> List[ChunkMetadata]:
        logger.debug("Creating metadata for %d chunks for %s", len(chunks), document.id)

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

        logger.debug("%s: reconstructed %d TextChunk objects", document.id, len(text_chunks))
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
            logger.warning("Document %s has no content to chunk", document.id)
            return []

        use_markdown_chunker = self.chunker_type == "structured_markdown"

        if self.chunker_type == "auto":
            if hasattr(document, "file_type") and document.file_type.lower() in [".md", ".markdown"]:
                use_markdown_chunker = True
            elif re.search(r"^#{1,6}\s+.+$", document.raw_content, re.MULTILINE):
                use_markdown_chunker = True

        if use_markdown_chunker:
            logger.info("%s: using structured markdown chunker", document.id)
            return self.structured_markdown_chunker.chunk_document(document)

        logger.info("%s: using recursive text chunker", document.id)
        doc_chunks = self.recursive_character_splitter.split_text(document.raw_content)
        return [chunk.page_content if isinstance(chunk, Document) else chunk for chunk in doc_chunks]

    def create_chunk_metadata(self, document, chunks: List[str]) -> List[ChunkMetadata]:
        return self.structured_markdown_chunker.create_chunk_metadata(document, chunks)

    def reconstruct_document(self, document, chunks: List[str], chunk_metadatas: List[ChunkMetadata]) -> List[TextChunk]:
        return self.structured_markdown_chunker.reconstruct_document(document, chunks, chunk_metadatas)


class PageLevelChunker:
    """Chunker that splits PDF documents by page first, then sub-splits long pages.

    - Splits document.raw_content by form-feed (\f) markers inserted by the PDF parser.
    - Detects repeated headers/footers and removes them.
    - Fixes common hyphenation issues across line breaks.
    - For long pages, uses RecursiveCharacterTextSplitter to sub-split.
    - Produces ChunkMetadata with page_number and chunk_strategy ('page' or 'page+recursive').
    """

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200) -> None:
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    def _detect_headers_footers(self, pages: list[str]) -> tuple[set[str], set[str]]:
        """Heuristic: top/bottom non-blank lines that repeat on >=60% pages treated as header/footer."""
        from collections import Counter

        def top_bottom_lines(txt: str) -> tuple[str, str]:
            lines = [l.strip() for l in (txt or "").splitlines() if l.strip()]
            top = lines[0] if lines else ""
            bot = lines[-1] if len(lines) > 1 else ""
            return top, bot

        tops, bots = Counter(), Counter()
        for p in pages:
            t, b = top_bottom_lines(p)
            if t:
                tops[t] += 1
            if b:
                bots[b] += 1
        threshold = max(1, int(0.6 * max(1, len(pages))))
        header_set = {t for t, c in tops.items() if c >= threshold}
        footer_set = {b for b, c in bots.items() if c >= threshold}
        return header_set, footer_set

    def _normalize_page(self, text: str, headers: set[str], footers: set[str]) -> tuple[str, int]:
        """Normalize a single page and report how many header/footer lines were removed.

        Returns: (normalized_text, removed_count)
        """
        lines = (text or "").splitlines()
        removed = 0
        # Strip global headers/footers if they match exactly after strip
        if lines and lines[0].strip() in headers:
            lines = lines[1:]
            removed += 1
        if len(lines) > 1 and lines[-1].strip() in footers:
            lines = lines[:-1]
            removed += 1
        page = "\n".join(lines)
        # Fix hyphenation across newlines: "foo-\nbar" -> "foobar"
        page = page.replace("-\n", "")
        # Collapse 3+ consecutive blank lines into 2
        page = re.sub(r"\n\s*\n\s*\n+", "\n\n", page)
        return page.strip(), removed

    def chunk_document_by_page(self, document) -> list[str]:
        raw = document.raw_content or ""
        # Prefer explicit pages list if present; fallback to form-feed separation.
        pages = getattr(document, "pages", None)
        if not pages:
            pages = raw.split("\f") if "\f" in raw else [raw]

        if not pages or (len(pages) == 1 and not pages[0].strip()):
            logger.warning("%s: PageLevelChunker found no pages", getattr(document, "id", "doc"))
            setattr(document, "_page_chunks", [])
            return []

        headers, footers = self._detect_headers_footers(pages)

        chunk_pairs: list[tuple[int, str]] = []  # (page_number, text)
        for idx, ptxt in enumerate(pages, start=1):
            norm, removed = self._normalize_page(ptxt, headers, footers)
            if not norm:
                continue
            if len(norm) <= self.chunk_size:
                chunk_pairs.append((idx, norm))
                sub_count = 1
            else:
                subs = self.splitter.split_text(norm)
                sub_count = 0
                for sub in subs:
                    sub_txt = sub.page_content if isinstance(sub, Document) else sub
                    if sub_txt and sub_txt.strip():
                        chunk_pairs.append((idx, sub_txt))
                        sub_count += 1

            try:
                logger.info(
                    "%s: page %d chars=%d -> norm=%d sub_chunks=%d removed_header_footer=%d",
                    getattr(document, "id", "doc"),
                    idx,
                    len(ptxt or ""),
                    len(norm or ""),
                    sub_count,
                    removed,
                )
            except Exception:
                pass

        # Stash for metadata construction
        setattr(document, "_page_chunks", chunk_pairs)
        return [t for _, t in chunk_pairs]

    def create_page_chunk_metadata(self, document, chunks: list[str]) -> list[ChunkMetadata]:
        pairs: list[tuple[int, str]] = getattr(document, "_page_chunks", []) or []
        # Safety: ensure length alignment
        if len(pairs) != len(chunks):
            # rebuild pairs from chunks assuming page 1 if unknown
            pairs = [(1, c) for c in chunks]

        # Determine which pages were sub-split
        from collections import Counter
        counts = Counter([pg for pg, _ in pairs])

        metas: list[ChunkMetadata] = []
        cursor = 0
        for page_num, text in pairs:
            word_count = len((text or "").split())
            # Try to locate in original raw content for positional metadata; may fail due to normalization
            start_index = (document.raw_content or "").find(text, cursor)
            if start_index == -1:
                start_index = (document.raw_content or "").find(text)
            end_index = start_index + len(text) if start_index != -1 else -1
            if end_index != -1:
                cursor = end_index

            meta = ChunkMetadata(
                start_index=start_index,
                end_index=end_index,
                word_count=word_count,
                language=getattr(document.metadata, "language", "en"),
                page_number=page_num,
                chunk_strategy="page+recursive" if counts.get(page_num, 0) > 1 else "page",
            )
            metas.append(meta)
        return metas

    def reconstruct_document(self, document, chunks: list[str], metas: list[ChunkMetadata]) -> list[TextChunk]:
        text_chunks: list[TextChunk] = []
        for i, (chunk_text, metadata) in enumerate(zip(chunks, metas)):
            chunk_id = f"{document.id}_chunk_{i}"
            prev_id = f"{document.id}_chunk_{i-1}" if i > 0 else None
            next_id = f"{document.id}_chunk_{i+1}" if i < len(chunks) - 1 else None
            text_chunks.append(
                TextChunk(
                    id=chunk_id,
                    document_id=document.id,
                    content=chunk_text,
                    metadata=metadata,
                    previous_chunk_id=prev_id,
                    next_chunk_id=next_id,
                )
            )
        logger.debug("%s: reconstructed %d page-level chunks", document.id, len(text_chunks))
        return text_chunks
