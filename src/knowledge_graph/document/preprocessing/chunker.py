import pstats
from typing import List, Dict, Optional, Tuple, Any
from src.knowledgeAgent.document.models.chunk import TextChunk, ChunkMetadata
import uuid
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import re
import argparse
import os


class MarkdownSection:
    """Represents a section in a markdown document with hierarchical structure"""
    
    def __init__(self, level: int, title: str, content: str = ""):
        self.level = level        # Header level (1 for #, 2 for ##, etc.)
        self.title = title        # Header text
        self.content = content    # Direct content (excluding subsections)
        self.subsections = []     # Child sections
        self.parent = None        # Parent section
        self.start_index = 0      # Start position in original document
        self.end_index = 0        # End position in original document
        
    def add_subsection(self, section: 'MarkdownSection') -> None:
        """Add a subsection to this section"""
        section.parent = self
        self.subsections.append(section)
        
    def full_content(self, include_headers: bool = True) -> str:
        """Returns content including all subsections"""
        result = ""
        if include_headers and self.title:
            # Add header with appropriate level
            result += ("#" * self.level) + " " + self.title + "\n\n"
        
        # Add direct content
        result += self.content
        
        # Add subsection content
        for subsection in self.subsections:
            result += subsection.full_content(include_headers)
            
        return result
        
    def size(self) -> int:
        """Calculate total characters in the section including subsections"""
        return len(self.full_content())
        
    def get_full_path(self) -> str:
        """Get the full hierarchical path to this section"""
        if self.parent is None:
            return self.title
        return self.parent.get_full_path() + " > " + self.title
        
    def __str__(self) -> str:
        return f"Section(level={self.level}, title='{self.title}', size={self.size()}, subsections={len(self.subsections)})"


class StructuredMarkdownChunker:
    """Chunks markdown text by respecting the document's header structure"""

    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200, max_depth: int = 4):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_depth = max_depth  # Maximum header depth to consider (1=h1, 2=h2, etc)
        self.fallback_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def parse_document(self, text: str) -> List[MarkdownSection]:
        """Parse markdown text into a hierarchical section structure"""
        # Regex to find headers: captures the level (number of #) and the title
        header_pattern = re.compile(r'^(#{1,6})\s+(.+?)(?:\s+#+)?$', re.MULTILINE)
        
        # Find all headers with their positions
        headers = []
        for match in header_pattern.finditer(text):
            level = len(match.group(1))  # Number of # characters
            title = match.group(2).strip()
            position = match.start()
            headers.append((level, title, position))
            
        # Add document end as a sentinel
        headers.append((0, "", len(text)))
        
        # Create root sections (level 1 headers)
        root_sections = []
        section_stack = []
        
        for i in range(len(headers) - 1):
            level, title, start = headers[i]
            next_start = headers[i + 1][2]
            
            # Skip headers deeper than max_depth
            if level > self.max_depth:
                continue
                
            # Create new section
            content_start = start + len("#" * level) + len(title) + 2  # +2 for "# " format
            content = text[content_start:next_start].strip()
            
            # Find first non-empty line to start content (skip the header line)
            content_lines = content.split('\n')
            if content_lines and content_lines[0].strip() == "":
                content = '\n'.join(content_lines[1:])
                
            section = MarkdownSection(level, title, content)
            section.start_index = start
            section.end_index = next_start
            
            # Find parent for this section based on level
            while section_stack and section_stack[-1].level >= level:
                section_stack.pop()
                
            if not section_stack:  # This is a root section
                root_sections.append(section)
            else:  # This is a subsection
                section_stack[-1].add_subsection(section)
                
            section_stack.append(section)
            
        return root_sections

    def chunk_section(self, section: MarkdownSection, max_size: int, depth: int = 1) -> List[str]:
        """Recursively chunk a section based on its structure"""
        chunks = []
        
        # If this section fits in a chunk, use it directly
        if section.size() <= max_size:
            chunks.append(section.full_content())
            return chunks
            
        # If we've reached max depth or there are no subsections,
        # use fallback chunking strategy
        if depth >= self.max_depth or not section.subsections:
            # Create a context header path
            context = ""
            current = section
            while current:
                if current.title:
                    prefix = "#" * current.level + " "
                    context = prefix + current.title + "\n\n" + context
                current = current.parent
                
            # Prepend context to content and chunk
            full_text = context + section.content
            fallback_chunks = self.fallback_splitter.split_text(full_text)
            chunks.extend(fallback_chunks)
            return chunks
            
        # Try to chunk by subsections
        current_chunk = ""
        current_sections = []
        section_header = ("#" * section.level) + " " + section.title + "\n\n" if section.title else ""
        
        # Add the section's direct content to the first chunk
        if section.content:
            current_chunk = section_header + section.content
        else:
            current_chunk = section_header
            
        # Process subsections
        for subsection in section.subsections:
            subsection_size = subsection.size()
            
            if subsection_size > max_size:
                # If we have accumulated content, create a chunk
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = ""
                
                # Recursively chunk this large subsection
                sub_chunks = self.chunk_section(subsection, max_size, depth + 1)
                chunks.extend(sub_chunks)
                
            elif len(current_chunk) + subsection_size > max_size:
                # Adding this subsection would exceed max size,
                # so finalize current chunk and start a new one
                chunks.append(current_chunk)
                
                # Start new chunk with context header
                current_chunk = section_header + subsection.full_content()
                
            else:
                # Add this subsection to current chunk
                current_chunk += subsection.full_content()
                
        # Don't forget the last chunk
        if current_chunk:
            chunks.append(current_chunk)
            
        return chunks

    def chunk_document(self, document: Any) -> List[str]:
        """Split document content into chunks respecting markdown structure"""
        print(f"Chunking document {document.id} using StructuredMarkdownChunker")
        
        if not document.raw_content:
            print("Warning: Document has no content to chunk")
            return []
            
        # Parse document into sections
        root_sections = self.parse_document(document.raw_content)
        print(f"Found {len(root_sections)} root sections in document")
        
        # Chunk each root section
        chunks = []
        for section in root_sections:
            section_chunks = self.chunk_section(section, self.chunk_size)
            chunks.extend(section_chunks)
            
        print(f"Created {len(chunks)} chunks")
        return chunks
        
    def create_chunk_metadata(self, document: Any, chunks: List[str]) -> List[ChunkMetadata]:
        """Generate metadata for each chunk"""
        print("Creating metadata for chunks")
        
        chunk_metadatas = []
        current_position = 0
        
        for i, chunk_text in enumerate(chunks):
            # Calculate basic metrics
            word_count = len(chunk_text.split())
            
            # Find the chunk's position in the original document
            start_index = document.raw_content.find(chunk_text, current_position)
            if start_index == -1:  # If not found, try from beginning
                start_index = document.raw_content.find(chunk_text)
            end_index = start_index + len(chunk_text) if start_index != -1 else -1
            
            # Update current position for next search
            current_position = end_index if end_index != -1 else current_position

            # Create metadata
            metadata = ChunkMetadata(
                start_index=start_index,
                end_index=end_index,
                word_count=word_count,
                language=document.metadata.language if hasattr(document.metadata, 'language') else 'en'
            )
            chunk_metadatas.append(metadata)
    
        return chunk_metadatas
    
    def reconstruct_document(self, document: Any, chunks: List[str], chunk_metadatas: List[ChunkMetadata]) -> List[TextChunk]:
        """Create TextChunk objects with metadata and navigation links"""
        text_chunks = []
        
        # Track indices for navigation
        for i, (chunk_text, metadata) in enumerate(zip(chunks, chunk_metadatas)):
            chunk_id = f"{document.id}_chunk_{i}"
            
            # Create previous/next links
            prev_id = f"{document.id}_chunk_{i-1}" if i > 0 else None
            next_id = f"{document.id}_chunk_{i+1}" if i < len(chunks) - 1 else None
            
            # Create chunk using metadata's indices
            chunk = TextChunk(
                id=chunk_id,
                document_id=document.id,
                content=chunk_text,
                metadata=metadata,
                previous_chunk_id=prev_id,
                next_chunk_id=next_id
            )
            text_chunks.append(chunk)
            
        print(f"Created {len(text_chunks)} text chunks")
        return text_chunks

class Chunker:
    """Handles document chunking with various strategies"""    
    def __init__(self, chunk_size=2000, chunk_overlap=200, chunker_type="auto"):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.chunker_type = chunker_type
        
        # Initialize different chunking strategies
        self.recursive_character_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )
        self.structured_markdown_chunker = StructuredMarkdownChunker(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            max_depth=4
        )
        
    def chunk_document(self, document) -> List[str]:
        """Split document content into chunks using the appropriate strategy"""
        if not document.raw_content:
            print("Warning: Document has no content to chunk")
            return []
            
        # Determine chunking strategy based on file type, content, or explicit choice
        use_markdown_chunker = self.chunker_type == "structured_markdown"
        
        # Use auto-detection if not explicitly set to structured_markdown
        if self.chunker_type == "auto":
            # Check if it's a markdown file or has markdown-like headers
            if hasattr(document, 'file_type') and document.file_type.lower() in ['.md', '.markdown']:
                use_markdown_chunker = True
            elif re.search(r'^#{1,6}\s+.+$', document.raw_content, re.MULTILINE):
                # Document has markdown headers, use markdown chunker
                use_markdown_chunker = True
            
        if use_markdown_chunker:
            print(f"Chunking document {document.id} using structured markdown chunker")
            return self.structured_markdown_chunker.chunk_document(document)
        else:
            print(f"Chunking document {document.id} using standard recursive chunker")
            doc_chunks = self.recursive_character_splitter.split_text(document.raw_content)
            chunks = [chunk.page_content if isinstance(chunk, Document) else chunk for chunk in doc_chunks]
            return chunks
    
    def create_chunk_metadata(self, document, chunks: List[str]) -> List[ChunkMetadata]:
        """Generate metadata for each chunk"""
        return self.structured_markdown_chunker.create_chunk_metadata(document, chunks)
    
    def reconstruct_document(self, document, chunks: List[str], chunk_metadatas: List[ChunkMetadata]) -> List[TextChunk]:
        """Create TextChunk objects with metadata and navigation links"""
        return self.structured_markdown_chunker.reconstruct_document(document, chunks, chunk_metadatas)


def test_markdown_chunker(file_path=None):
    """Test function to demonstrate the markdown chunker with a real file"""
    import os
    
    # If no file path is provided, try to get one from command line arguments
    if file_path is None:
        parser = argparse.ArgumentParser(description='Test the markdown chunker on a real file')
        parser.add_argument('--file', type=str, help='Path to a markdown file to process')
        args, _ = parser.parse_known_args()
        
        if args.file:
            file_path = args.file
        else:
            # Default path if none provided
            file_path = os.path.expanduser("~/Documents/sample.md")
            if not os.path.exists(file_path):
                print(f"Warning: Default file {file_path} not found.")
                # Create a simple sample markdown file
                sample_markdown = """# Sample Markdown File
                
This is an automatically generated sample file for testing the markdown chunker.
                
## Section 1
                
This is section 1 content.
                
### Subsection 1.1
                
This is subsection 1.1 content.
                
## Section 2
                
This is section 2 content.
                """
                # Check if we can write to the default path
                try:
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    with open(file_path, 'w') as f:
                        f.write(sample_markdown)
                    print(f"Created sample file at {file_path}")
                except Exception as e:
                    print(f"Could not create sample file: {e}")
                    # Use the sample as content instead of file
                    file_path = None
                    content = sample_markdown
    
    print("\n\n=== TESTING MARKDOWN CHUNKER ===\n")
    
    # Get content from file if we have a valid file path
    content = ""
    if file_path and os.path.exists(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"Read content from {file_path}")
        except Exception as e:
            print(f"Error reading file: {e}")
            # If we can't read the file, use a simple default content
            content = "# Default Content\n\nThis is a fallback content since the file couldn't be read."
    elif not 'content' in locals():
        # Fallback content if no valid file and content wasn't defined
        content = "# Default Content\n\nThis is default content for testing the markdown chunker."
    
    # Create a mock document
    class MockDocument:
        def __init__(self, content, file_path=None):
            self.id = "test_doc_" + (os.path.basename(file_path) if file_path else "sample")
            self.raw_content = content
            self.file_path = file_path
            self.metadata = type('obj', (object,), {'language': 'en'})
    
    doc = MockDocument(content, file_path)
    
    # Initialize the chunker with a small chunk size to force splitting
    chunker = StructuredMarkdownChunker(chunk_size=8000, chunk_overlap=100, max_depth=3)
    
    # Parse the document into sections
    print("\nParsing document into sections...")
    sections = chunker.parse_document(doc.raw_content)
    
    # Print the section hierarchy
    def print_section_tree(section, indent=0):
        print(" " * indent + f"- {section.level}: {section.title} ({len(section.content)} chars, {len(section.subsections)} subsections)")
        for subsection in section.subsections:
            print_section_tree(subsection, indent + 2)
    
    print(f"\nSection Hierarchy (found {len(sections)} root sections):")
    for section in sections:
        print_section_tree(section)
        
    # Chunk the document
    print("\nChunking document...")
    chunks = chunker.chunk_document(doc)
    
    # Print the chunks
    print(f"\nCreated {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks):
        print(f"\n--- Chunk {i+1} ---")
        preview = chunk
        # Make the preview more readable by replacing multiple newlines
        preview = preview.replace("\n\n", "[NEWLINE]").replace("\n", " ").replace("[NEWLINE]", "\n\n")
        print(preview)
        print(f"Size: {len(chunk)} characters")

    print("\n=== TEST COMPLETE ===\n")
    
    return chunker


if __name__ == "__main__":
    import sys
    # Use sample file for testing
    file_path = "./sample_documents/sample.md" if len(sys.argv) < 2 else sys.argv[1]
    test_markdown_chunker(file_path)


