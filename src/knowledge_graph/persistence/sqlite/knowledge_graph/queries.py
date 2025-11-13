"""SQLite DDL for Knowledge Base and Ontologies (KB-level)."""

CREATE_KNOWLEDGE_BASES_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_bases (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  slug        TEXT NOT NULL,
  name        TEXT NOT NULL,
  owner_id    TEXT,
  description TEXT,
  created_at  TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  updated_at  TEXT NOT NULL DEFAULT (CURRENT_TIMESTAMP),
  UNIQUE(owner_id, slug)
);
"""

CREATE_INDEX_KB_CREATED_AT = """
CREATE INDEX IF NOT EXISTS idx_knowledge_bases_created_at
ON knowledge_bases(created_at);
"""

CREATE_INDEX_KB_OWNER_SLUG = """
CREATE INDEX IF NOT EXISTS idx_kb_owner_slug
ON knowledge_bases(owner_id, slug);
"""

CREATE_KNOWLEDGE_BASE_ONTOLOGIES_TABLE = """
CREATE TABLE IF NOT EXISTS knowledge_base_ontologies (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  kb_id         INTEGER,
  document_id   INTEGER,
  name          TEXT,
  specification TEXT CHECK (specification IS NULL OR json_valid(specification)),
  status        TEXT,
  version       INTEGER DEFAULT 1,
  FOREIGN KEY (kb_id)       REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  FOREIGN KEY (document_id) REFERENCES documents(id)       ON DELETE CASCADE
);
"""

