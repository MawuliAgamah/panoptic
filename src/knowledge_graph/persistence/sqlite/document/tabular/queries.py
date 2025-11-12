"""SQLite DDL + queries for tabular (CSV) documents."""

# Table stores CSV-specific metadata and links a document to a knowledge base.
# The foreign keys assume `documents(document_id)` and `knowledge_bases(id)` exist.

CREATE_TABULAR_DOCUMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS csv_profiles (
    document_id TEXT PRIMARY KEY,
    kb_id TEXT,
    delimiter TEXT,
    encoding TEXT,
    headers TEXT,
    headers_normalized TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
"""

CREATE_CSV_MAPPING_TABLE = """
CREATE TABLE IF NOT EXISTS csv_mappings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    kb_id TEXT NOT NULL UNIQUE,
    ontology_id TEXT,
    mapping_specification JSON, UNIQUE(document_id, kb_id) ON CONFLICT REPLACE  
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)

"""
SAVE_TABULAR_DOCUMENT = """
INSERT INTO tabular_documents (
    document_id,
    kb_id,
    delimiter,
    encoding,
    headers,
    headers_normalized,
    sample_rows,
    profile_json,
    created_at,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
ON CONFLICT(document_id) DO UPDATE SET
    kb_id = excluded.kb_id,
    delimiter = excluded.delimiter,
    encoding = excluded.encoding,
    headers = excluded.headers,
    headers_normalized = excluded.headers_normalized,
    sample_rows = excluded.sample_rows,
    profile_json = excluded.profile_json,
    updated_at = CURRENT_TIMESTAMP
RETURNING document_id;
"""

INSERT_CSV_MAPPING = """
INSERT INTO csv_mappings (document_id, kb_id, ontology_id, mapping_specification)
VALUES (?, ?, ?, ?);
"""