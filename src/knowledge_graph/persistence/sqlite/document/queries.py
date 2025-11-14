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

CREATE_DOCUMENT_ONTOLOGIES_TABLE = """
CREATE TABLE IF NOT EXISTS document_ontologies (
  id            INTEGER PRIMARY KEY,
  document_id   INTEGER NOT NULL,
  specification TEXT    NOT NULL CHECK (json_valid(specification)), -- JSON payload
  status        TEXT    DEFAULT 'proposed' CHECK (status IN ('proposed','approved','rejected','active')),
  version       INTEGER DEFAULT 1,
  proposed_by   TEXT,
  reviewed_by   TEXT,
  created_at    TEXT    DEFAULT (CURRENT_TIMESTAMP),
  approved_at   TEXT,
  is_canonical  INTEGER DEFAULT 0 CHECK (is_canonical IN (0,1)),
  FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
"""

SAVE_DOCUMENT = """
INSERT INTO documents (
  id, 
  ontology_id,
  kb_id, 
  file_name, 
  file_path, 
  file_type, 
  file_size, 
  file_hash, 
  status,
  processed_at
)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
  kb_id = excluded.kb_id,
  ontology_id = excluded.ontology_id,
  file_name = excluded.file_name,
  file_path = excluded.file_path,
  file_type = excluded.file_type,
  file_size = excluded.file_size,
  file_hash = excluded.file_hash,
  status = excluded.status,
  processed_at = excluded.processed_at;
"""

UPDATE_DOCUMENT_ONTOLOGY_ID = """
UPDATE documents SET ontology_id = ? WHERE id = ?;
"""

INSERT_DOCUMENT_ONTOLOGY = """
INSERT INTO document_ontologies (
  document_id, specification, status, version, proposed_by, reviewed_by, created_at, approved_at, is_canonical
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
"""

CREATE_INDEX_DOCUMENT_ONTOLOGIES_DOCUMENT_VERSION = """
CREATE INDEX IF NOT EXISTS idx_document_ontologies_document_version
ON document_ontologies (document_id, version);
"""

CREATE_INDEX_DOCUMENT_ONTOLOGIES_STATUS = """
CREATE INDEX IF NOT EXISTS idx_document_ontologies_status
ON document_ontologies (status);
"""

