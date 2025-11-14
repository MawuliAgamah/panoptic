from __future__ import annotations

"""SQLite facade for persistence adapters (documents, KG, ER).

This class centralizes SQLite wiring so callers can construct one object
with a db_path and obtain typed repositories/stores implementing the
corresponding ports.
"""

from typing import Optional
import logging
import os
from pathlib import Path

from .document.document_repository import SQLiteDocumentRepository
from .document.tabular.tabular_doc_repository import SQLiteTabularDocumentRepository
from .document.pdf.pdf_doc_repository import SQLitePdfDocumentRepository
from .knowledge_graph.graph_store import SQLiteGraphRepository
from .entity_resolution.entity_resolution_store import SQLiteEntityResolutionRepository
from .knowledge_graph.knowledge_base_repository import SQLiteKnowledgeBaseRepository
from ...settings.settings import Settings

logger = logging.getLogger(__name__)



class SqlLite:
    """SQLite persistence facade providing access to all repositories and stores."""
    
    def __init__(self, settings: Settings):
        """Initialize SqlLite facade with database path from settings.
        
        Args:
            settings: Settings object containing database configuration
        """
        db_path = settings.db.db_location
        # Resolve relative paths to absolute
        if not Path(db_path).is_absolute():
            # Try to resolve relative to current working directory first
            db_path = str(Path(db_path).resolve())
        self.db_path = db_path
        self._ensure_db_dir()
    
    def _ensure_db_dir(self) -> None:
        """Ensure the database directory exists."""
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)

    def drop_all_tables(self, delete_file: bool = True) -> None:
        """Drop all tables in the database. Use with caution - this deletes all data!
        
        Args:
            delete_file: If True, delete the entire database file instead of just dropping tables
        """
        import sqlite3
        import os
        
        # If delete_file is True, just delete the file and return
        if delete_file:
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                logger.info(f"Deleted database file: {self.db_path}")
                # Also delete WAL and SHM files if they exist
                wal_file = f"{self.db_path}-wal"
                shm_file = f"{self.db_path}-shm"
                if os.path.exists(wal_file):
                    os.remove(wal_file)
                if os.path.exists(shm_file):
                    os.remove(shm_file)
                return
            else:
                logger.info("Database file does not exist, nothing to delete")
                return
        
        # Ensure directory exists
        self._ensure_db_dir()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                
                # Disable foreign keys temporarily to allow dropping in any order
                cur.execute("PRAGMA foreign_keys=OFF")
                
                # Get all table names
                cur.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name NOT LIKE 'sqlite_%'
                    ORDER BY name
                """)
                tables = [row[0] for row in cur.fetchall()]
                
                if not tables:
                    logger.info("No tables to drop")
                    # Vacuum to reclaim space
                    cur.execute("VACUUM")
                    conn.commit()
                    return
                
                logger.warning(f"Dropping {len(tables)} tables: {', '.join(tables)}")
                
                # Drop each table
                for table in tables:
                    try:
                        cur.execute(f"DROP TABLE IF EXISTS {table}")
                        logger.debug(f"Dropped table: {table}")
                    except Exception as e:
                        logger.error(f"Error dropping table {table}: {e}")
                
                # Vacuum to reclaim space and ensure clean state
                cur.execute("VACUUM")
                
                # Re-enable foreign keys
                cur.execute("PRAGMA foreign_keys=ON")
                conn.commit()
                
                logger.info("All tables dropped successfully and database vacuumed")
        except Exception as e:
            logger.error(f"Error dropping tables: {e}")
            raise

    # Create all database tables if they don't exist -------------------------------------------------
    def create_tables(self) -> None:
        """Ensure database file exists and base tables are created."""
        try:
            # Create repositories (they handle their own table creation)
            document_repository = SQLiteDocumentRepository(self.db_path)
            knowledge_base_repository = SQLiteKnowledgeBaseRepository(self.db_path)
            graph_repository = SQLiteGraphRepository(self.db_path)
            entity_resolution_repository = SQLiteEntityResolutionRepository(self.db_path)
            
            # Initialize tables
            logger.info("Initializing database tables...")
            document_repository.create_tables()
            knowledge_base_repository.create_tables()
            graph_repository.create_tables()
            entity_resolution_repository.ensure_schema()
            logger.info("All database tables initialized successfully")
        except Exception as e:
            logger.error("Error creating tables: %s", e)
            raise

    # Adapters ----------------------------------------------------------
    def document_repository(self) -> SQLiteDocumentRepository:
        return SQLiteDocumentRepository(self.db_path)
    
    def tabular_document_repository(self) -> SQLiteTabularDocumentRepository:
        return SQLiteTabularDocumentRepository(self.db_path)
    
    def graph_repository(self) -> SQLiteGraphRepository:
        return SQLiteGraphRepository(self.db_path)

    def entity_resolution_repository(self) -> SQLiteEntityResolutionRepository:
        return SQLiteEntityResolutionRepository(self.db_path)

    def knowledge_base_repository(self) -> SQLiteKnowledgeBaseRepository:
        return SQLiteKnowledgeBaseRepository(self.db_path)
