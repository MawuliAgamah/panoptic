from __future__ import annotations

"""SQLite implementation for DocumentRepository.

This adapter implements direct SQL operations for persisting and retrieving
documents and chunks without relying on a shared repository.
"""

from typing import Optional, List
import sqlite3
import json
import logging
from pathlib import Path
from datetime import datetime

from .tabular.tabular_doc_repository import SQLiteTabularDocumentRepository
from .pdf.pdf_doc_repository import SQLitePdfDocumentRepository
from ....data_structs.document import Document, DocumentNew

from .queries import (
    CREATE_DOCUMENTS_TABLE,
    CREATE_DOCUMENT_ONTOLOGIES_TABLE,
    SAVE_DOCUMENT,
)

logger = logging.getLogger(__name__)


class SQLiteDocumentRepository():
    """SQLite implementation of DocumentRepository port."""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_db_dir()
    
    def _ensure_db_dir(self) -> None:
        """Ensure the database directory exists."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
    
    def create_tables(self) -> bool:
        """Ensure tables are initialized."""
        logger.info("Creating document tables...")
        tabular_document_repository = SQLiteTabularDocumentRepository(self.db_path)
        logger.info("Creating tabular document tables...")
        tabular_document_repository.create_tables()
        logger.info("Creating pdf document tables...")
        pdf_document_repository = SQLitePdfDocumentRepository(self.db_path)
        pdf_document_repository.create_tables()
        logger.info("Creating document ontologies tables...")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                
                # Create pdf_document table
                cur.execute(CREATE_DOCUMENTS_TABLE)
                # Create document_ontologies table
                cur.execute(CREATE_DOCUMENT_ONTOLOGIES_TABLE)
                
                
                conn.commit()
                logger.info("Document tables created/verified")
                return True
        except Exception as e:
            logger.error(f"Error creating document tables: {e}")
            return False

    def save_pdf_document(self, document: Document) -> bool:
        """Save a PDF document to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(SAVE_DOCUMENT, (document.id, document.kb_id, document.file_name, document.file_path, document.file_type, document.file_size, document.file_hash, document.chunks))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving PDF document: {e}")
            return False
        
        
    def save_document_ontology(self, document_ontology: DocumentOntology) -> bool:
        """Save a document ontology to the database."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(UPSERT_DOCUMENT_ONTOLOGY, (document_ontology.id, document_ontology.document_id, document_ontology.specification, document_ontology.status, document_ontology.version, document_ontology.proposed_by, document_ontology.reviewed_by, document_ontology.created_at, document_ontology.approved_at, document_ontology.is_canonical))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving document ontology: {e}")
            return False

    def save_document(self, document: DocumentNew) -> bool:
        """Insert or update a document (and associated chunks if present)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(SAVE_DOCUMENT, (
                            document.id,
                            document.ontology_id,
                            document.kb_id,
                            document.file_name,
                            document.file_path,
                            document.file_type,
                            document.file_size,
                            document.file_hash,
                            document.status,
                            document.processed_at,
                        ))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving document: {e}")
            return False

    def get_document(self, document_id: str) -> Optional[Document]:
        """Retrieve a document by its identifier."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                
                # Try to convert to int, otherwise use hash
                try:
                    doc_id_int = int(document_id)
                except (ValueError, TypeError):
                    doc_id_int = abs(hash(document_id)) % (10 ** 9)
                
                # Get document
                cur.execute(
                    "SELECT id, kb_id, file_name, file_path, file_type, file_size, file_hash, chunks, created_at, processed_at FROM pdf_document WHERE id = ?",
                    (doc_id_int,)
                )
                row = cur.fetchone()
                
                if not row:
                    return None
                
                # Get chunks
                cur.execute(
                    "SELECT chunk_index, content, token_count, start_char, end_char, embedding_vector FROM document_chunks WHERE pdf_document_id = ? ORDER BY chunk_index",
                    (doc_id_int,)
                )
                chunk_rows = cur.fetchall()
                
                # Reconstruct document
                from ....data_structs.document.metadata import DocumentMetadata
                from ....data_structs.document.chunk import TextChunk, ChunkMetadata
                
                # Parse chunks JSON if available
                text_chunks = []
                if row[7]:  # chunks JSON field
                    try:
                        chunks_data = json.loads(row[7])
                        for chunk_data in chunks_data:
                            metadata = ChunkMetadata(
                                start_index=chunk_data.get('metadata', {}).get('start_index', 0),
                                end_index=chunk_data.get('metadata', {}).get('end_index', 0),
                                page_number=chunk_data.get('metadata', {}).get('page_number'),
                            )
                            chunk = TextChunk(
                                id=chunk_data.get('id', ''),
                                document_id=document_id,
                                content=chunk_data.get('content', ''),
                                metadata=metadata,
                            )
                            text_chunks.append(chunk)
                    except (json.JSONDecodeError, KeyError):
                        pass
                
                # If no chunks from JSON, use chunks from table
                if not text_chunks and chunk_rows:
                    for chunk_row in chunk_rows:
                        metadata = ChunkMetadata(
                            start_index=chunk_row[3] or 0,
                            end_index=chunk_row[4] or 0,
                        )
                        chunk = TextChunk(
                            id=f"{document_id}_chunk_{chunk_row[0]}",
                            document_id=document_id,
                            content=chunk_row[1] or '',
                            metadata=metadata,
                        )
                        text_chunks.append(chunk)
                
                # Create metadata
                metadata = DocumentMetadata(
                    document_id=document_id,
                    custom_fields={
                        'kb_id': str(row[1]) if row[1] else None,
                        'file_type': row[4],
                        'file_size': row[5],
                    }
                )
                
                # Create document
                document = Document(
                    id=document_id,
                    filename=row[2] or '',
                    file_path=row[3] or '',
                    file_type=row[4] or '',
                    file_size=row[5] or 0,
                    title=row[2] or '',  # Use filename as title
                    raw_content='',  # Not stored in this schema
                    clean_content='',  # Not stored in this schema
                    metadata=metadata,
                    textChunks=text_chunks,
                )
                
                return document
        except Exception as e:
            logger.error(f"Error retrieving document {document_id}: {e}")
            return None
    
    def update_document(self, document: Document) -> bool:
        """Update an existing document."""
        # save_document uses INSERT ... ON CONFLICT DO UPDATE, so it handles updates
        return self.save_document(document)

    def delete_document(self, document_id: str) -> bool:
        """Delete a document and its related rows."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")
                
                # Try to convert to int, otherwise use hash
                try:
                    doc_id_int = int(document_id)
                except (ValueError, TypeError):
                    doc_id_int = abs(hash(document_id)) % (10 ** 9)
                
                # Delete document (chunks will be deleted via CASCADE)
                cur.execute("DELETE FROM pdf_document WHERE id = ?", (doc_id_int,))
                conn.commit()
                
                logger.debug(f"Document deleted: {document_id}")
                return cur.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return False
    
    def list_documents(self, *, kb_id: Optional[str] = None) -> List[str]:
        """List document identifiers (optionally filtered by knowledge base)."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                
                if kb_id:
                    try:
                        kb_id_int = int(kb_id)
                        cur.execute(
                            "SELECT id FROM pdf_document WHERE kb_id = ? ORDER BY created_at DESC",
                            (kb_id_int,)
                        )
                    except (ValueError, TypeError):
                        # If kb_id is not an integer, return empty list
                        return []
                else:
                    cur.execute("SELECT id FROM pdf_document ORDER BY created_at DESC")
                
                rows = cur.fetchall()
                # Convert integer IDs back to strings
                return [str(row[0]) for row in rows]
        except Exception as e:
            logger.error(f"Error listing documents: {e}")
            return []
