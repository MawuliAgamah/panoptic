import sqlite3
from typing import Any
from .queries import (
    CREATE_TABULAR_DOCUMENTS_TABLE,
    CREATE_CSV_MAPPINGS_TABLE,
    CREATE_INDEX_CSV_MAPPINGS_DOCUMENT,
    CREATE_INDEX_CSV_MAPPINGS_ONTOLOGY,
    INSERT_TABULAR_DOCUMENT,
)
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
                cur.execute("PRAGMA foreign_keys=ON")

                # csv_profiles
                logger.info("Creating csv_profiles table if it doesn't exist")
                cur.execute(CREATE_TABULAR_DOCUMENTS_TABLE)

                # csv_mappings + indexes
                logger.info("Creating csv_mappings table if it doesn't exist")
                cur.execute(CREATE_CSV_MAPPINGS_TABLE)
                logger.info("Creating indexes for csv_mappings table")
                cur.execute(CREATE_INDEX_CSV_MAPPINGS_DOCUMENT)
                logger.info("Creating indexes for csv_mappings_ontology table")
                cur.execute(CREATE_INDEX_CSV_MAPPINGS_ONTOLOGY)

                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return False

    def save_tabular_document(self, tabular_document: Any) -> bool:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute(
                    INSERT_TABULAR_DOCUMENT,
                    (
                        tabular_document.document_id,
                        getattr(tabular_document, "delimiter", ","),
                        int(getattr(tabular_document, "has_header", True)),
                        getattr(tabular_document, "encoding", "utf-8"),
                        getattr(tabular_document, "row_count", None),
                        getattr(tabular_document, "column_count", None),
                        getattr(tabular_document, "headers", None),
                        getattr(tabular_document, "sample_rows", None),
                        getattr(tabular_document, "profile_stats", None),
                    ),
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error saving tabular document: {e}")
            return False
