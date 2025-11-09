-- Knowledge bases table for namespaced persistence
CREATE TABLE IF NOT EXISTS knowledge_bases (
    id TEXT PRIMARY KEY,
    slug TEXT NOT NULL,
    name TEXT NOT NULL,
    owner_id TEXT,
    description TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(owner_id, slug)
);

CREATE INDEX IF NOT EXISTS idx_kb_owner_slug ON knowledge_bases(owner_id, slug);

