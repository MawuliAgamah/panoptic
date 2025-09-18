"""
Script which handles everything related to processing to be embedded.
"""
# import os
# import sys
# import glob


from dataclasses import dataclass
from src.knowledgeAgent.document.models.metadata import DocumentMetadata
from src.knowledgeAgent.document.models.document import Document
from src.knowledgeAgent.document.preprocessing.chunker import Chunker
from src.knowledgeAgent.document.preprocessing.parser import ParserFactory


import uuid
import os

class DocumentManager:
    """Construct Document Object"""
    def __init__(self,llm_service):
        self.name = "Document builder"
        self.llm_service = llm_service

    def make_new_document(self, document_path, document_id):
       """Create a new Document instance based on file information"""
       try:
           # Get file metadata
           print(f"Creating document for {document_path}")
           
           if not os.path.exists(document_path):
               print(f"Error: File not found: {document_path}")
               return None
               
           file_size = os.path.getsize(document_path)
           filename = os.path.basename(document_path)
       
           print("creating metadata")
           metadata = DocumentMetadata(
               title=os.path.splitext(filename)[0],
               document_id=document_id,
               metadata_id=str(uuid.uuid4()),
           )
           
           # Create the Document instance
           document = Document(
               id=document_id,
               filename=filename,
               file_path=document_path,
               file_type=os.path.splitext(document_path)[1],
               file_size=file_size,
               title=os.path.splitext(filename)[0],  # Use filename without extension as title
               raw_content="",  # Will be filled during parsing
               clean_content="",  # Will be filled during cleaning
               metadata=metadata,  # Inline metadata creation
               textChunks=[]  # Will be filled during chunking
           )
           print("document initialized and loaded with contents")
           document = self._load_document_contents(document)
           return document
       except Exception as e:
           print(f"Error creating document: {e}")
           return None

    def _load_document_contents(self, document):
        """Parse document content based on document type"""
        print(f"Parsing document {document.id} of type {document.file_type}")
        # Get appropriate parser for document type
        parser = ParserFactory.get_parser(document.file_type)
        # Parse document
        raw_content = parser.parse(document.file_path)
        # Update document with content
        document.raw_content = raw_content
        document.is_parsed = True
        return document
    
    def clean_document(self, document):
        pass
    
    def chunk_document(self, document):
        """Process document through chunking pipeline"""
        print(f"Chunking document {document.id}")
        
        # Create chunker with default strategy
        chunker = Chunker(chunk_size=1000, chunk_overlap=200, chunker_type="structured_markdown")
        

        chunks = chunker.chunk_document(document)
        chunk_metadatas = chunker.create_chunk_metadata(document, chunks)
        text_chunks = chunker.reconstruct_document(document, chunks, chunk_metadatas)
        
        # Update document with chunks
        document.textChunks = text_chunks
        document.is_chunked = True
        
        print(f"Document chunking complete: {len(text_chunks)} chunks")
        return document

    def enrich_document_chunks(self, document):
        """Use LLM service to enrich document chunks"""
        if not document.textChunks:
            print(f"Warning: Document {document.id} has no chunks to enrich")
            return document
        
        print(f"Enriching {len(document.textChunks)} chunks with LLM")
        for chunk in document.textChunks:
            # Extract topics and keywords
            raw_topics = self.llm_service.extract_topics(chunk.content)
            raw_keywords = self.llm_service.extract_keywords(chunk.content)
            
            # Clean topics - extract from dict and remove any # symbols
            cleaned_topics = []
            if isinstance(raw_topics, dict) and 'topics' in raw_topics:
                cleaned_topics = [t.replace('#', '').strip() for t in raw_topics['topics']]
            elif isinstance(raw_topics, list):
                cleaned_topics = [t.replace('#', '').strip() for t in raw_topics]
            
            # Clean keywords - extract from dict and remove any # symbols
            cleaned_keywords = []
            if isinstance(raw_keywords, dict) and 'keywords' in raw_keywords:
                cleaned_keywords = [k.replace('#', '').strip() for k in raw_keywords['keywords']]
            elif isinstance(raw_keywords, list):
                cleaned_keywords = [k.replace('#', '').strip() for k in raw_keywords]
            
            # Ensure we don't exceed max items
            chunk.metadata.topics = cleaned_topics # Max 3 topics
            chunk.metadata.keywords = cleaned_keywords # Max 3 keywords

        print(f"Document enrichment complete")
        return document

    def generate_document_level_metadata(self, document):
        """Generate document-level metadata using LLM service"""
        try:
            # Get document content for analysis
            content = document.raw_content
            
            # Extract topics and keywords from the full document
            raw_topics = self.llm_service.extract_topics(content)
            raw_keywords = self.llm_service.extract_keywords(content)
            
            # Clean topics - extract from dict and remove any # symbols
            cleaned_topics = []
            if isinstance(raw_topics, dict) and 'topics' in raw_topics:
                cleaned_topics = [t.replace('#', '').strip() for t in raw_topics['topics']]
            elif isinstance(raw_topics, list):
                cleaned_topics = [t.replace('#', '').strip() for t in raw_topics]
            
            # Clean keywords - extract from dict and remove any # symbols
            cleaned_keywords = []
            if isinstance(raw_keywords, dict) and 'keywords' in raw_keywords:
                cleaned_keywords = [k.replace('#', '').strip() for k in raw_keywords['keywords']]
            elif isinstance(raw_keywords, list):
                cleaned_keywords = [k.replace('#', '').strip() for k in raw_keywords]
            
            # Update document metadata
            document.metadata.tags = cleaned_topics[:5]  # Use topics as tags
            document.metadata.categories = cleaned_keywords[:5]  # Use keywords as categories
            
            # Calculate word count
            document.metadata.word_count = len(content.split())
            
            # Extract section headers (assuming markdown format)
            if document.file_type.lower() in ['.md', '.markdown']:
                import re
                headers = re.findall(r'^#{1,6}\s+(.+)$', content, re.MULTILINE)
                document.metadata.section_headers = headers
            
            # Set processing flags
            document.is_metadata_generated = True
            
            print(f"Generated metadata for document {document.id}")
            return document
            
        except Exception as e:
            print(f"Error generating document metadata: {e}")
            return document














