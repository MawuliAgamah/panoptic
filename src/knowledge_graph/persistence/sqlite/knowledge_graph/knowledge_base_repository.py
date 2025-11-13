from __future__ import annotations

from typing import Optional, List
import logging
from ....ports.knowledge_base import KnowledgeBaseRepository
from ....data_structs.knowledge_base import KnowledgeBase
import sqlite3
from datetime import datetime
from .queries import (
    CREATE_KNOWLEDGE_BASES_TABLE,
    CREATE_INDEX_KB_CREATED_AT,
    CREATE_INDEX_KB_OWNER_SLUG,
    CREATE_KNOWLEDGE_BASE_ONTOLOGIES_TABLE,
)

class SQLiteKnowledgeBaseRepository(KnowledgeBaseRepository):
    """SQLite implementation of KnowledgeBaseRepository.

    Note: Keep SQL inline for now; migrate to central queries if needed.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()
        self._logger = logging.getLogger("knowledge_graph.persistence.sqlite.kb")
    
    def create_tables(self) -> bool:
        self._logger.info("Ensuring Knowledge Base and KB Ontologies tables exist")
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("PRAGMA foreign_keys=ON")

                # Ensure base KB schema
                self._ensure_schema()

                # Ensure KB ontologies table (nullable kb_id/document_id FKs)
                cur.execute(CREATE_KNOWLEDGE_BASE_ONTOLOGIES_TABLE)

                conn.commit()
                return True
        except Exception as e:
            self._logger.error(f"Error creating KB tables: {e}")
            return False

    def create(self, name: str, slug: str, *, owner_id: Optional[str] = None, description: Optional[str] = None) -> KnowledgeBase:
        self._logger.info(f"KB(create) sqlite slug={slug} owner_id={owner_id or '-'}")
        existing = self.get_by_slug(slug, owner_id=owner_id)
        if existing:
            self._logger.info(f"KB(create) exists kb_id={existing.id} slug={existing.slug}")
            return existing

        now = datetime.utcnow()
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO knowledge_bases (slug, name, owner_id, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (
                    slug,
                    name,
                    owner_id,
                    description,
                    now.isoformat(),
                    now.isoformat(),
                ),
            )
            conn.commit()
            # Get the inserted/updated ID
            kb_id = cur.lastrowid
            if not kb_id:
                # If conflict occurred, fetch the existing ID
                cur.execute(
                    "SELECT id FROM knowledge_bases WHERE slug = ? AND (owner_id = ? OR (owner_id IS NULL AND ? IS NULL))",
                    (slug, owner_id, owner_id)
                )
                row = cur.fetchone()
                kb_id = row[0] if row else None
        
        created = self.get_by_slug(slug, owner_id=owner_id)
        if not created:
            # Fallback: create object manually if query fails
            created = KnowledgeBase(
                id=str(kb_id) if kb_id else "0",
                name=name,
                slug=slug,
                owner_id=owner_id,
                description=description,
                created_at=now,
                updated_at=now,
            )
        self._logger.info(f"KB(create) upserted kb_id={created.id} slug={created.slug}")
        return created

    def get_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, slug, name, owner_id, description, created_at, updated_at FROM knowledge_bases WHERE id = ?",
                (int(kb_id),),
            )
            row = cur.fetchone()
            if not row:
                return None
            return KnowledgeBase(
                id=str(row[0]), slug=row[1], name=row[2], owner_id=row[3], description=row[4], created_at=row[5], updated_at=row[6]
            )

    def get_by_slug(self, slug: str, *, owner_id: Optional[str] = None) -> Optional[KnowledgeBase]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            if owner_id is not None:
                cur.execute(
                    "SELECT id, slug, name, owner_id, description, created_at, updated_at FROM knowledge_bases WHERE slug = ? AND owner_id = ?",
                    (slug, owner_id),
                )
            else:
                cur.execute(
                    "SELECT id, slug, name, owner_id, description, created_at, updated_at FROM knowledge_bases WHERE slug = ?",
                    (slug,),
                )
            row = cur.fetchone()
            if not row:
                return None
            return KnowledgeBase(
                id=str(row[0]), slug=row[1], name=row[2], owner_id=row[3], description=row[4], created_at=row[5], updated_at=row[6]
            )

    def list(self, *, owner_id: Optional[str] = None) -> List[KnowledgeBase]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            if owner_id is not None:
                cur.execute(
                    "SELECT id, slug, name, owner_id, description, created_at, updated_at FROM knowledge_bases WHERE owner_id = ? ORDER BY created_at DESC",
                    (owner_id,),
                )
            else:
                cur.execute(
                    "SELECT id, slug, name, owner_id, description, created_at, updated_at FROM knowledge_bases ORDER BY created_at DESC"
                )
            rows = cur.fetchall() or []
            self._logger.info(f"KB(list) sqlite owner_id={owner_id or '-'} count={len(rows)}")
            return [
                KnowledgeBase(
                    id=str(r[0]), slug=r[1], name=r[2], owner_id=r[3], description=r[4], created_at=r[5], updated_at=r[6]
                )
                for r in rows
            ]

    def _ensure_schema(self) -> None:
        """Ensure knowledge_bases table schema exists."""
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute("PRAGMA foreign_keys=ON")
            cur.execute(CREATE_KNOWLEDGE_BASES_TABLE)
            cur.execute(CREATE_INDEX_KB_CREATED_AT)
            cur.execute(CREATE_INDEX_KB_OWNER_SLUG)
            conn.commit()


