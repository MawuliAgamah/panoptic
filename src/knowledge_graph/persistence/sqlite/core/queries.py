"""SQLite DDL for core objects: documents, entities, relationships (model-aligned)."""

# Documents
CREATE_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
  id           INTEGER PRIMARY KEY,
  kb_id        INTEGER NOT NULL,
  ontology_id  INTEGER,
  file_name    TEXT NOT NULL,
  file_path    TEXT,
  file_type    TEXT NOT NULL CHECK (file_type IN ('PDF','MD','TXT','CSV')),
  file_size    INTEGER,
  file_hash    TEXT,
  status       TEXT DEFAULT 'pending' CHECK (status IN ('pending','processing','completed','failed')),
  created_at   TEXT DEFAULT (CURRENT_TIMESTAMP),
  processed_at TEXT,
  FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);
"""

CREATE_INDEX_DOCUMENTS_KB_ID = """
CREATE INDEX IF NOT EXISTS idx_documents_kb_id ON documents(kb_id);
"""

CREATE_INDEX_DOCUMENTS_FILE_HASH = """
CREATE INDEX IF NOT EXISTS idx_documents_file_hash ON documents(file_hash);
"""

CREATE_INDEX_DOCUMENTS_STATUS = """
CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
"""

CREATE_INDEX_DOCUMENTS_FILE_TYPE = """
CREATE INDEX IF NOT EXISTS idx_documents_file_type ON documents(file_type);
"""

# Entities
CREATE_ENTITIES_TABLE = """
CREATE TABLE IF NOT EXISTS entities (
  id                   INTEGER PRIMARY KEY,
  kb_id                INTEGER NOT NULL,
  document_id          INTEGER NOT NULL,
  entity_definition_id INTEGER NOT NULL,
  entity_type          TEXT NOT NULL,
  entity_label         TEXT NOT NULL,
  source_row_index     INTEGER,
  properties           TEXT NOT NULL CHECK (json_valid(properties)),
  created_at           TEXT DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (kb_id)       REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  FOREIGN KEY (document_id) REFERENCES documents(id)       ON DELETE CASCADE
);
"""

CREATE_INDEX_ENTITIES_KB_ID = """
CREATE INDEX IF NOT EXISTS idx_entities_kb_id ON entities(kb_id);
"""

CREATE_INDEX_ENTITIES_DOCUMENT_ID = """
CREATE INDEX IF NOT EXISTS idx_entities_document_id ON entities(document_id);
"""

CREATE_INDEX_ENTITIES_DEFINITION_ID = """
CREATE INDEX IF NOT EXISTS idx_entities_definition_id ON entities(entity_definition_id);
"""

CREATE_INDEX_ENTITIES_TYPE = """
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
"""

CREATE_INDEX_ENTITIES_TYPE_LABEL = """
CREATE INDEX IF NOT EXISTS idx_entities_type_label ON entities(entity_type, entity_label);
"""

# Relationships
CREATE_RELATIONSHIPS_TABLE = """
CREATE TABLE IF NOT EXISTS relationships (
  id                         INTEGER PRIMARY KEY,
  kb_id                      INTEGER NOT NULL,
  document_id                INTEGER NOT NULL,
  relationship_definition_id INTEGER,
  relationship_type          TEXT NOT NULL,
  source_entity_id           INTEGER NOT NULL,
  target_entity_id           INTEGER NOT NULL,
  properties                 TEXT CHECK (properties IS NULL OR json_valid(properties)),
  confidence_score           REAL,
  created_at                 TEXT DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (kb_id)           REFERENCES knowledge_bases(id) ON DELETE CASCADE,
  FOREIGN KEY (document_id)     REFERENCES documents(id)       ON DELETE CASCADE,
  FOREIGN KEY (source_entity_id) REFERENCES entities(id)       ON DELETE CASCADE,
  FOREIGN KEY (target_entity_id) REFERENCES entities(id)       ON DELETE CASCADE
);
"""

CREATE_INDEX_RELATIONSHIPS_KB_ID = """
CREATE INDEX IF NOT EXISTS idx_relationships_kb_id ON relationships(kb_id);
"""

CREATE_INDEX_RELATIONSHIPS_DOCUMENT_ID = """
CREATE INDEX IF NOT EXISTS idx_relationships_document_id ON relationships(document_id);
"""

CREATE_INDEX_RELATIONSHIPS_SOURCE_ID = """
CREATE INDEX IF NOT EXISTS idx_relationships_source_id ON relationships(source_entity_id);
"""

CREATE_INDEX_RELATIONSHIPS_TARGET_ID = """
CREATE INDEX IF NOT EXISTS idx_relationships_target_id ON relationships(target_entity_id);
"""

CREATE_INDEX_RELATIONSHIPS_TYPE = """
CREATE INDEX IF NOT EXISTS idx_relationships_type ON relationships(relationship_type);
"""

CREATE_INDEX_RELATIONSHIPS_DEFINITION_ID = """
CREATE INDEX IF NOT EXISTS idx_relationships_definition_id ON relationships(relationship_definition_id);
"""
