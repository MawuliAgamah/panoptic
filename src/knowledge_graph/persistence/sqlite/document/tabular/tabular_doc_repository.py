import sqlite3
from .queries import CREATE_TABULAR_DOCUMENTS_TABLE, INSERT_TABULAR_DOCUMENT
import logging

logger = logging.getLogger(__name__)

class SQLiteTabularDocumentRepository():
    def __init__(self, db_path: str):
        self.db_path = db_path

    def create_tables(self) -> bool:
        logger.info("Creating tabular document table if it doesn't exist")
        try:
            with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(CREATE_TABULAR_DOCUMENTS_TABLE)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return False

    def save_tabular_document(self, tabular_document: TabularDocument) -> bool:
        try:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(INSERT_TABULAR_DOCUMENT,
                (tabular_document.document_id, tabular_document.kb_id, tabular_document.delimiter, tabular_document.encoding, tabular_document.headers, tabular_document.headers_normalized, tabular_document.created_at, tabular_document.updated_at)
            )
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving tabular document: {e}")
            return False