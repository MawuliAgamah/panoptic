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

