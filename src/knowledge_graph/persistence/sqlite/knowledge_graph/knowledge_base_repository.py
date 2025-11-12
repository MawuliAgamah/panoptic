from __future__ import annotations

from typing import Optional, List
import logging
from ....ports.knowledge_base import KnowledgeBaseRepository
from ....data_structs.knowledge_base import KnowledgeBase
import sqlite3
from datetime import datetime
import uuid
from logger_config import logger

class SQLiteKnowledgeBaseRepository(KnowledgeBaseRepository):
    """SQLite implementation of KnowledgeBaseRepository.

    Note: Keep SQL inline for now; migrate to central queries if needed.
    """

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._ensure_schema()
        self._logger = logging.getLogger("knowledge_graph.persistence.sqlite.kb")
    
    def create_tables(self) -> bool:
        logger.info("Creating Knowledge Base, Entities, Relationships, Document Ontology, Knowledge Base Ontology tables if they don't exist")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(CREATE_KNOWLEDGE_BASES_TABLE)
            cur.execute(CREATE_ENTITIES_TABLE)
            cur.execute(CREATE_RELATIONSHIPS_TABLE)
            cur.execute(CREATE_DOCUMENT_ONTOLOGY_TABLE)
            cur.execute(CREATE_KNOWLEDGE_BASE_ONTOLOGY_TABLE)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating table: {e}")
            return False

    def create(self, name: str, slug: str, *, owner_id: Optional[str] = None, description: Optional[str] = None) -> KnowledgeBase:
        self._logger.info(f"KB(create) sqlite slug={slug} owner_id={owner_id or '-'}")
        existing = self.get_by_slug(slug, owner_id=owner_id)
        if existing:
            self._logger.info(f"KB(create) exists kb_id={existing.id} slug={existing.slug}")
            return existing

        kb = KnowledgeBase(
            id=str(uuid.uuid4()),
            name=name,
            slug=slug,
            owner_id=owner_id,
            description=description,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO knowledge_bases (id, slug, name, owner_id, description, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(owner_id, slug) DO UPDATE SET
                    name = excluded.name,
                    description = excluded.description,
                    updated_at = excluded.updated_at
                """,
                (
                    kb.id,
                    kb.slug,
                    kb.name,
                    kb.owner_id,
                    kb.description,
                    kb.created_at.isoformat(),
                    kb.updated_at.isoformat(),
                ),
            )
            conn.commit()
        created = self.get_by_slug(slug, owner_id=owner_id) or kb
        self._logger.info(f"KB(create) upserted kb_id={created.id} slug={created.slug}")
        return created

    def get_by_id(self, kb_id: str) -> Optional[KnowledgeBase]:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT id, slug, name, owner_id, description, created_at, updated_at FROM knowledge_bases WHERE id = ?",
                (kb_id,),
            )
            row = cur.fetchone()
            if not row:
                return None
            return KnowledgeBase(
                id=row[0], slug=row[1], name=row[2], owner_id=row[3], description=row[4], created_at=row[5], updated_at=row[6]
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
                id=row[0], slug=row[1], name=row[2], owner_id=row[3], description=row[4], created_at=row[5], updated_at=row[6]
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
                    id=r[0], slug=r[1], name=r[2], owner_id=r[3], description=r[4], created_at=r[5], updated_at=r[6]
                )
                for r in rows
            ]

    def _ensure_schema(self) -> None:
        from pathlib import Path
        script_path = Path(__file__).with_name("migrations").joinpath("v001_kb.sql")
        with sqlite3.connect(self.db_path) as conn:
            if script_path.exists():
                with open(script_path, "r", encoding="utf-8") as f:
                    conn.executescript(f.read())
            else:
                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS knowledge_bases (
                        id TEXT PRIMARY KEY,
                        slug TEXT NOT NULL,
                        name TEXT NOT NULL,
                        owner_id TEXT,
                        description TEXT,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        UNIQUE(owner_id, slug)
                    )
                    """
                )
                cur.execute(
                    "CREATE INDEX IF NOT EXISTS idx_kb_owner_slug ON knowledge_bases(owner_id, slug)"
                )
            conn.commit()
