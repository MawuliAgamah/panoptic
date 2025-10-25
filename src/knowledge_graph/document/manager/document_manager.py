"""
Script which handles everything related to processing to be embedded.
"""
# import os
# import sys
# import glob


from dataclasses import dataclass
from ..models.metadata import DocumentMetadata
from ..models.document import Document
from ..preprocessing.chunker import Chunker
from ..preprocessing.parser import ParserFactory
from ...knowledge_graph.service import KnowledgeGraphService


import uuid
import os

class DocumentManager:
    """Construct Document Object"""
    def __init__(self, llm_service, db_client=None, kg_service=None, llm_provider="openai"):
        self.name = "Document builder"
        self.llm_service = llm_service
        self.db_client = db_client

        # Use provided kg_service or create new one
        if kg_service:
            self.kg_service = kg_service
        elif db_client:
            self.kg_service = KnowledgeGraphService(
                db_client=db_client,
                llm_service=llm_service,
                llm_provider=llm_provider
            )
        else:
            # Fallback for backward compatibility
            from ...llm.kg_extractor.service import KGExtractionService
            self.kg_service = KGExtractionService(llm_provider="mock")

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
        """Clean Obsidian markdown content for better kg-gen processing"""
        import re

        if not document.raw_content:
            document.clean_content = ""
            document.wiki_links = []
            document.is_preprocessed = True
            return document

        content = document.raw_content

        # Remove embedded files first (they start with !)
        content = re.sub(r'!\[\[(.*?)\]\]', '', content)    # Embedded files ![[file]]

        # Extract wiki links (now that embedded files are removed)
        wiki_links = re.findall(r'\[\[(.*?)\]\]', content)
        document.wiki_links = wiki_links

        # Remove Obsidian-specific syntax
        content = re.sub(r'\[\[(.*?)\]\]', r'\1', content)  # Wiki links [[Page]] → Page
        content = re.sub(r'%%.*?%%', '', content, flags=re.DOTALL)  # Comments %%text%%

        # Clean standard markdown formatting
        content = re.sub(r'\*\*(.*?)\*\*', r'\1', content)  # Bold **text** → text
        content = re.sub(r'\*(.*?)\*', r'\1', content)      # Italic *text* → text
        content = re.sub(r'`([^`]+)`', r'\1', content)      # Inline code `text` → text
        content = re.sub(r'#{1,6}\s+', '', content)         # Headers # → content

        # Clean excessive whitespace but preserve code blocks
        # First preserve code blocks
        code_blocks = []
        def preserve_code_block(match):
            code_blocks.append(match.group(0))
            return f"__CODE_BLOCK_{len(code_blocks)-1}__"

        content = re.sub(r'```.*?```', preserve_code_block, content, flags=re.DOTALL)

        # Clean whitespace
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)  # Multiple newlines → double newline

        # Restore code blocks
        for i, code_block in enumerate(code_blocks):
            content = content.replace(f"__CODE_BLOCK_{i}__", code_block)

        # Final cleanup
        content = content.strip()

        document.clean_content = content
        document.is_preprocessed = True

        print(f"Content cleaned: {len(document.raw_content)} → {len(content)} chars, extracted {len(wiki_links)} wiki links")

        return document
    
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
            print(f"🔍 Extracting topics and keywords from document {document.id}")
            raw_topics = self.llm_service.extract_topics(content)
            raw_keywords = self.llm_service.extract_keywords(content)
            print(f"📊 Raw topics: {raw_topics}")
            print(f"📊 Raw keywords: {raw_keywords}")
            
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
            
            # Update document metadata - preserve existing domain/tags and add LLM-extracted ones
            # Preserve existing tags (from user input) and add LLM-extracted topics
            existing_tags = getattr(document.metadata, 'tags', [])
            print(f"🏷️ Existing tags: {existing_tags}")
            print(f"🏷️ Cleaned topics: {cleaned_topics[:5]}")
            document.metadata.tags = list(set(existing_tags + cleaned_topics[:5]))  # Combine and deduplicate
            print(f"🏷️ Final tags: {document.metadata.tags}")
            
            # Preserve existing categories (from user input) and add LLM-extracted keywords
            existing_categories = getattr(document.metadata, 'categories', [])
            print(f"📂 Existing categories: {existing_categories}")
            print(f"📂 Cleaned keywords: {cleaned_keywords[:5]}")
            document.metadata.categories = list(set(existing_categories + cleaned_keywords[:5]))  # Combine and deduplicate
            print(f"📂 Final categories: {document.metadata.categories}")
            
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

    def extract_knowledge_graph(self, document):
        """Extract knowledge graph from document using intelligent processing decisions"""
        try:
            print(f"Starting KG extraction for document {document.id}")

            # Ensure document is cleaned first
            if not document.clean_content and document.raw_content:
                print("Document not cleaned yet, cleaning now...")
                self.clean_document(document)

            # Validate content suitability for KG extraction
            if not document.validate_content_for_kg():
                print(f"Document {document.id} not suitable for KG extraction")
                document.is_kg_extracted = True  # Mark as processed to avoid retry
                document.knowledge_graph = {'entities': set(), 'relations': []}
                return document

            # Decide between document-level vs chunk-level processing
            if document.should_use_document_level_kg():
                print(f"Using document-level KG extraction (estimated tokens: {document.estimate_token_count()})")
                result = self.kg_service.extract_from_document(document)
            else:
                print(f"Using chunk-level KG extraction (document too large: {document.estimate_token_count()} tokens)")

                # Ensure document is chunked
                if not document.textChunks:
                    print("Document not chunked yet, chunking now...")
                    self.chunk_document(document)

                # Extract text from chunks
                chunk_texts = [chunk.content for chunk in document.textChunks if chunk.content.strip()]

                if chunk_texts:
                    result = self.kg_service.extract_from_chunks(chunk_texts, document.id)

                    # Manually update document metadata since we didn't use extract_from_document
                    document.knowledge_graph = result
                    document.is_kg_extracted = True
                    from datetime import datetime
                    document.kg_extracted_at = datetime.now()
                    document.kg_extraction_metadata = {
                        'strategy_used': 'chunk-level',
                        'chunk_count': len(chunk_texts),
                        'entity_count': len(result.get('entities', set())),
                        'relation_count': len(result.get('relations', []))
                    }
                else:
                    print("No valid chunks found for KG extraction")
                    result = {'entities': set(), 'relations': []}
                    document.knowledge_graph = result
                    document.is_kg_extracted = True

            entity_count = len(result.get('entities', set()))
            relation_count = len(result.get('relations', []))
            print(f"KG extraction complete for document {document.id}: {entity_count} entities, {relation_count} relations")

            return document

        except Exception as e:
            print(f"Error during KG extraction for document {document.id}: {e}")
            # Set empty KG to avoid repeated processing attempts
            document.knowledge_graph = {'entities': set(), 'relations': []}
            document.is_kg_extracted = True
            return document

    def process_document_complete(self, document_path, document_id, enable_kg_extraction=True, enable_enrichment=True):
        """Complete document processing pipeline with KG extraction"""
        try:
            print(f"Starting complete processing for document: {document_path}")

            # Step 1: Create and load document
            document = self.make_new_document(document_path, document_id)
            if not document:
                print(f"Failed to create document from {document_path}")
                return None

            # Step 2: Clean document content
            document = self.clean_document(document)

            # Step 3: Generate document-level metadata
            document = self.generate_document_level_metadata(document)

            # Step 4: Extract knowledge graph (intelligent processing decision)
            if enable_kg_extraction:
                document = self.extract_knowledge_graph(document)

            # Step 5: Chunk document (if not already done during KG extraction)
            if not document.textChunks:
                document = self.chunk_document(document)

            # Step 6: Enrich chunks with LLM (optional)
            if enable_enrichment:
                document = self.enrich_document_chunks(document)

            print(f"Complete processing finished for document {document.id}")
            return document

        except Exception as e:
            print(f"Error in complete document processing: {e}")
            return None














