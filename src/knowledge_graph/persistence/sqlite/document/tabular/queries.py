"""SQLite DDL + queries for tabular (CSV) documents."""



# CSV profiles: structure and statistics for a CSV document
CREATE_CSV_PROFILES_TABLE = """
CREATE TABLE IF NOT EXISTS csv_profiles (
  id             INTEGER PRIMARY KEY,
  document_id    INTEGER NOT NULL UNIQUE,
  delimiter      TEXT    DEFAULT ',',
  has_header     INTEGER DEFAULT 1 CHECK (has_header IN (0,1)),
  encoding       TEXT    DEFAULT 'utf-8',
  row_count      INTEGER,
  column_count   INTEGER,
  headers        TEXT CHECK (headers IS NULL OR json_valid(headers)),
  sample_rows    TEXT CHECK (sample_rows IS NULL OR json_valid(sample_rows)),
  profile_stats  TEXT CHECK (profile_stats IS NULL OR json_valid(profile_stats)),
  created_at     TEXT DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
"""

UPSERT_CSV_PROFILE = """
INSERT INTO csv_profiles (
  document_id, delimiter, has_header, encoding, row_count, column_count,
  headers, sample_rows, profile_stats
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(document_id) DO UPDATE SET
  delimiter = excluded.delimiter,
  has_header = excluded.has_header,
  encoding = excluded.encoding,
  row_count = excluded.row_count,
  column_count = excluded.column_count,
  headers = excluded.headers,
  sample_rows = excluded.sample_rows,
  profile_stats = excluded.profile_stats
RETURNING id;
"""



# CSV mappings: mapping spec from CSV to KG ontology
CREATE_CSV_MAPPINGS_TABLE = """
CREATE TABLE IF NOT EXISTS csv_mappings (
  id           INTEGER PRIMARY KEY,
  ontology_id  INTEGER NOT NULL UNIQUE,
  document_id  INTEGER NOT NULL,
  mapping_spec TEXT    NOT NULL CHECK (json_valid(mapping_spec)),
  created_at   TEXT DEFAULT (CURRENT_TIMESTAMP),
  validated_at TEXT,
  FOREIGN KEY (ontology_id) REFERENCES document_ontologies(id) ON DELETE CASCADE,
  FOREIGN KEY (document_id) REFERENCES documents(id)          ON DELETE CASCADE
);
"""

CREATE_INDEX_CSV_MAPPINGS_DOCUMENT = """
CREATE INDEX IF NOT EXISTS idx_csv_mappings_document ON csv_mappings(document_id);
"""

CREATE_INDEX_CSV_MAPPINGS_ONTOLOGY = """
CREATE INDEX IF NOT EXISTS idx_csv_mappings_ontology ON csv_mappings(ontology_id);
"""

INSERT_CSV_MAPPING = """
INSERT INTO csv_mappings (ontology_id, document_id, mapping_spec, validated_at)
VALUES (?, ?, ?, ?)
ON CONFLICT(ontology_id) DO UPDATE SET
  document_id = excluded.document_id,
  mapping_spec = excluded.mapping_spec,
  validated_at = excluded.validated_at;
"""

