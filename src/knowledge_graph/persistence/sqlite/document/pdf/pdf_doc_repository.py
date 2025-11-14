import sqlite3
from typing import Any
from .queries import (
    CREATE_PDF_DOCUMENT_TABLE,
    CREATE_PDF_DOCUMENT_CHUNKS_TABLE,
    UPSERT_PDF_DOCUMENT,
    INSERT_PDF_DOCUMENT_CHUNK,
)
import logging

logger = logging.getLogger(__name__)
# from knowledge_graph.data_structs.document.document import CSVDocument


class SQLitePdfDocumentRepository():
    def __init__(self, db_path: str):
        self.db_path = db_path

    def create_tables(self) -> bool:
        logger.info("Creating pdf document table if it doesn't exist")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")

                # csv_profiles
                logger.info("Creating pdf_document table if it doesn't exist")
                cur.execute(CREATE_PDF_DOCUMENT_TABLE)

                # csv_mappings + indexes
                logger.info("Creating document_chunks table if it doesn't exist")
                cur.execute(CREATE_PDF_DOCUMENT_CHUNKS_TABLE)
                logger.info("Creating indexes for document_chunks table")
                cur.execute(CREATE_INDEX_PDF_DOCUMENT_CHUNKS_DOC_IDX)

                # pdf_document_chunks + indexes
                logger.info("Creating pdf_document_chunks table if it doesn't exist")
                cur.execute(CREATE_PDF_DOCUMENT_CHUNKS_TABLE)
                logger.info("Creating indexes for pdf_document_chunks table")
                cur.execute(CREATE_INDEX_PDF_DOCUMENT_CHUNKS_DOC_IDX)

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return False
    
    

    def save_pdf_document(self, pdf_document: Any) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    UPSERT_PDF_DOCUMENT,
                    (
                        pdf_document.document_id,
                        pdf_document.kb_id,
                        pdf_document.file_name,
                        pdf_document.file_path,
                        pdf_document.file_type,
                        pdf_document.file_size,
                        pdf_document.file_hash,
                        pdf_document.chunks,
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving pdf document: {e}")
            return False