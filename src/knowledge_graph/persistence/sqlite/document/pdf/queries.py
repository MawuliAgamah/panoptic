"""SQLite DDL + queries for PDF/Markdown-like documents and chunks."""

CREATE_PDF_DOCUMENT_TABLE = """
CREATE TABLE IF NOT EXISTS pdf_document (
  id           INTEGER PRIMARY KEY,
  kb_id        INTEGER NOT NULL,
  file_name    TEXT NOT NULL,
  file_path    TEXT,
  file_type    TEXT NOT NULL CHECK (file_type IN ('PDF','MD','TXT','CSV')),
  file_size    INTEGER,
  file_hash    TEXT,
  chunks       TEXT,
  created_at   TEXT DEFAULT (CURRENT_TIMESTAMP),
  processed_at TEXT,
  FOREIGN KEY (id)   REFERENCES documents(id)       ON DELETE CASCADE,
  FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id) ON DELETE CASCADE
);
"""

CREATE_DOCUMENT_CHUNKS_TABLE = """
CREATE TABLE IF NOT EXISTS document_chunks (
  id               INTEGER PRIMARY KEY,
  pdf_document_id  INTEGER NOT NULL,
  chunk_index      INTEGER NOT NULL,
  content          TEXT NOT NULL,
  token_count      INTEGER,
  start_char       INTEGER,
  end_char         INTEGER,
  embedding_vector BLOB,
  created_at       TEXT DEFAULT (CURRENT_TIMESTAMP),
  FOREIGN KEY (pdf_document_id) REFERENCES pdf_document(id) ON DELETE CASCADE
);
"""

CREATE_INDEX_DOCUMENT_CHUNKS_DOC_IDX = """
CREATE INDEX IF NOT EXISTS idx_doc_chunks_doc_idx ON document_chunks(pdf_document_id, chunk_index);
"""

UPSERT_PDF_DOCUMENT = """
INSERT INTO pdf_document (
  id, kb_id, file_name, file_path, file_type, file_size, file_hash, chunks
) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(id) DO UPDATE SET
  kb_id = excluded.kb_id,
  file_name = excluded.file_name,
  file_path = excluded.file_path,
  file_type = excluded.file_type,
  file_size = excluded.file_size,
  file_hash = excluded.file_hash,
  chunks = excluded.chunks;
"""

INSERT_DOCUMENT_CHUNK = """
INSERT INTO document_chunks (
  pdf_document_id, chunk_index, content, token_count, start_char, end_char, embedding_vector
) VALUES (?, ?, ?, ?, ?, ?, ?);
"""
