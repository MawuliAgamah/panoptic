CREATE_DOCUMENT_TABLE = """
CREATE TABLE IF NOT EXISTS documents (
    document_id TEXT PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    hash TEXT,
    document_type TEXT,
    title TEXT,
    summary TEXT,
    raw_content TEXT,
    clean_content TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_modified TIMESTAMP
)
"""

CREATE_CHUNK_TABLE = """
CREATE TABLE IF NOT EXISTS chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    word_count INTEGER,
    token_count INTEGER,
    language TEXT,
    topics TEXT,
    keywords TEXT,
    start_index INTEGER,
    end_index INTEGER,
    previous_chunk_id INTEGER,
    next_chunk_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (previous_chunk_id) REFERENCES chunks(id),
    FOREIGN KEY (next_chunk_id) REFERENCES chunks(id)
)
"""

SAVE_DOCUMENT = """
INSERT INTO documents (
    document_id, file_path, hash, document_type, title, summary, 
    raw_content, clean_content, created_at, updated_at, last_modified
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(document_id) DO UPDATE SET
    file_path = excluded.file_path,
    hash = excluded.hash,
    document_type = excluded.document_type,
    title = excluded.title,
    summary = excluded.summary,
    raw_content = excluded.raw_content,
    clean_content = excluded.clean_content,
    updated_at = excluded.updated_at,
    last_modified = excluded.last_modified
RETURNING document_id
"""

SAVE_CHUNK = """
INSERT INTO chunks (
    document_id, content, chunk_index, word_count, token_count,
    language, topics, keywords, start_index, end_index,
    previous_chunk_id, next_chunk_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
"""

DOCUMENT_EXISTS_QUERY = """
SELECT document_id FROM documents WHERE document_id = ?
"""

GET_DOCUMENT_WITH_CHUNKS = """
SELECT 
    d.*,
    c.id as chunk_id,
    c.document_id,
    c.content,
    c.chunk_index,
    c.word_count,
    c.token_count,
    c.language,
    c.topics,
    c.keywords,
    c.start_index,
    c.end_index,
    c.previous_chunk_id,
    c.next_chunk_id,
    c.created_at as chunk_created_at
FROM documents d
LEFT JOIN chunks c ON d.document_id = c.document_id
WHERE d.document_id = ?
ORDER BY c.chunk_index
"""


CREATE_DOCUMENT_ONTOLOGY_TABLE = """
CREATE TABLE IF NOT EXISTS document_ontology (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_id TEXT NOT NULL,
    ontology TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE
)
"""

SAVE_DOCUMENT_ONTOLOGY = """
INSERT INTO document_ontology (
    document_id, ontology
) VALUES (?, ?)
ON CONFLICT(document_id) DO UPDATE SET
    ontology = excluded.ontology,
    updated_at = CURRENT_TIMESTAMP
"""

# Get Document DATA
GET_DOCUMENT_DATA = """
SELECT * FROM documents WHERE document_id = ?
"""

GET_CHUNK_DATA = """
SELECT * FROM chunks WHERE document_id = ?
"""

CREATE_ENTITY_TABLE = """
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL,
    category TEXT NOT NULL,
    document_id TEXT NOT NULL,
    chunk_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
)
"""

CREATE_RELATIONSHIP_TABLE = """
CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    relation TEXT NOT NULL,
    context TEXT,
    document_id TEXT NOT NULL,
    chunk_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(document_id) ON DELETE CASCADE,
    FOREIGN KEY (chunk_id) REFERENCES chunks(id) ON DELETE CASCADE
)
"""

SAVE_ENTITY = """
INSERT INTO entities (
    entity_id, name, type, category, document_id, chunk_id
) VALUES (?, ?, ?, ?, ?, ?)
ON CONFLICT(entity_id) DO UPDATE SET
    name = excluded.name,
    type = excluded.type,
    category = excluded.category
"""

SAVE_RELATIONSHIP = """
INSERT INTO relationships (
    relationship_id, source_entity_id, target_entity_id, relation, context, document_id, chunk_id
) VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(relationship_id) DO UPDATE SET
    relation = excluded.relation,
    context = excluded.context
"""

GET_ENTITIES_BY_DOCUMENT = """
SELECT * FROM entities WHERE document_id = ?
"""

GET_RELATIONSHIPS_BY_DOCUMENT = """
SELECT r.*, 
       e1.name as source_name, e1.type as source_type, e1.category as source_category,
       e2.name as target_name, e2.type as target_type, e2.category as target_category
FROM relationships r
JOIN entities e1 ON r.source_entity_id = e1.entity_id
JOIN entities e2 ON r.target_entity_id = e2.entity_id
WHERE r.document_id = ?
"""

GET_ENTITIES_BY_CHUNK = """
SELECT * FROM entities WHERE chunk_id = ?
"""

GET_RELATIONSHIPS_BY_CHUNK = """
SELECT r.*, 
       e1.name as source_name, e1.type as source_type, e1.category as source_category,
       e2.name as target_name, e2.type as target_type, e2.category as target_category
FROM relationships r
JOIN entities e1 ON r.source_entity_id = e1.entity_id
JOIN entities e2 ON r.target_entity_id = e2.entity_id
WHERE r.chunk_id = ?
"""