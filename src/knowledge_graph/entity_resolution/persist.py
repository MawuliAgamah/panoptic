from __future__ import annotations

import sqlite3
from typing import Iterable, List, Dict, Tuple, Optional, Any
from dataclasses import asdict

from ..core.db.db_client import DatabaseClient
from .models import EntityMention, ResolvedEntity


DDL = {
    "resolved_entities": """
    CREATE TABLE IF NOT EXISTS resolved_entities (
        resolved_id TEXT PRIMARY KEY,
        primary_name TEXT NOT NULL,
        normalized_key TEXT NOT NULL,
        type TEXT,
        category TEXT,
        mention_count INTEGER DEFAULT 0,
        doc_count INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(normalized_key, type)
    )
    """,
    "entity_resolution_map": """
    CREATE TABLE IF NOT EXISTS entity_resolution_map (
        entity_id TEXT PRIMARY KEY,
        resolved_id TEXT NOT NULL,
        strategy TEXT NOT NULL DEFAULT 'exact',
        confidence REAL NOT NULL DEFAULT 1.0,
        normalized_key TEXT NOT NULL,
        document_id TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    "resolved_relationships": """
    CREATE TABLE IF NOT EXISTS resolved_relationships (
        resolved_rel_id TEXT PRIMARY KEY,
        subject_resolved_id TEXT NOT NULL,
        predicate TEXT NOT NULL,
        object_resolved_id TEXT NOT NULL,
        weight INTEGER NOT NULL DEFAULT 0,
        doc_count INTEGER NOT NULL DEFAULT 0,
        first_seen_at TEXT,
        last_seen_at TEXT,
        UNIQUE(subject_resolved_id, predicate, object_resolved_id)
    )
    """,
    "resolved_relationship_mentions": """
    CREATE TABLE IF NOT EXISTS resolved_relationship_mentions (
        resolved_rel_id TEXT NOT NULL,
        relationship_id TEXT NOT NULL,
        document_id TEXT,
        chunk_id INTEGER,
        context TEXT,
        page INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(resolved_rel_id, relationship_id)
    )
    """,
}


def _conn(db: DatabaseClient) -> sqlite3.Connection:
    svc = getattr(db, "sqlite_service", None)
    if not svc or not hasattr(svc, "repository"):
        raise ValueError("SQLite service not initialized on DatabaseClient")
    path = svc.repository.db_path
    return sqlite3.connect(path)


def ensure_schema(db: DatabaseClient) -> None:
    with _conn(db) as conn:
        cur = conn.cursor()
        for sql in DDL.values():
            cur.execute(sql)
        conn.commit()


def fetch_mentions(db: DatabaseClient, doc_ids: Optional[List[str]] = None) -> List[EntityMention]:
    sql = "SELECT entity_id, name, type, category, document_id, chunk_id, created_at FROM entities"
    params: Tuple = tuple()
    if doc_ids:
        placeholders = ",".join(["?"] * len(doc_ids))
        sql += f" WHERE document_id IN ({placeholders})"
        params = tuple(doc_ids)
    mentions: List[EntityMention] = []
    with _conn(db) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        for row in cur.fetchall():
            mentions.append(
                EntityMention(
                    entity_id=row[0],
                    name=row[1],
                    type=row[2],
                    category=row[3],
                    document_id=row[4],
                    chunk_id=row[5],
                    created_at=row[6],
                )
            )
    return mentions


def upsert_resolved_entities(db: DatabaseClient, items: Iterable[ResolvedEntity]) -> int:
    sql = (
        "INSERT INTO resolved_entities (resolved_id, primary_name, normalized_key, type, category, mention_count, doc_count)"
        " VALUES (?, ?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(resolved_id) DO UPDATE SET"
        "   primary_name = excluded.primary_name,"
        "   normalized_key = excluded.normalized_key,"
        "   type = excluded.type,"
        "   category = excluded.category,"
        "   mention_count = excluded.mention_count,"
        "   doc_count = excluded.doc_count,"
        "   updated_at = CURRENT_TIMESTAMP"
    )
    count = 0
    with _conn(db) as conn:
        cur = conn.cursor()
        batch = [
            (
                it.resolved_id,
                it.primary_name,
                it.normalized_key,
                it.type,
                it.category,
                it.mention_count,
                it.doc_count,
            )
            for it in items
        ]
        if batch:
            cur.executemany(sql, batch)
            count = cur.rowcount if cur.rowcount is not None else len(batch)
        conn.commit()
    return count


def upsert_entity_resolution_map(db: DatabaseClient, mappings: List[Tuple[str, str, str, str, float]]) -> int:
    """Upsert rows into entity_resolution_map.

    Each mapping tuple: (entity_id, resolved_id, normalized_key, document_id, strategy, confidence)
    """
    sql = (
        "INSERT INTO entity_resolution_map (entity_id, resolved_id, normalized_key, document_id, strategy, confidence)"
        " VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(entity_id) DO UPDATE SET"
        "   resolved_id = excluded.resolved_id,"
        "   normalized_key = excluded.normalized_key,"
        "   document_id = excluded.document_id,"
        "   strategy = excluded.strategy,"
        "   confidence = excluded.confidence"
    )
    with _conn(db) as conn:
        cur = conn.cursor()
        if mappings:
            cur.executemany(sql, mappings)
        conn.commit()
        return cur.rowcount if cur.rowcount is not None else len(mappings)


def fetch_relationships(db: DatabaseClient, doc_ids: Optional[List[str]] = None) -> List[Tuple]:
    sql = (
        "SELECT relationship_id, source_entity_id, target_entity_id, relation, context, document_id, chunk_id, created_at"
        " FROM relationships"
    )
    params: Tuple = tuple()
    if doc_ids:
        placeholders = ",".join(["?"] * len(doc_ids))
        sql += f" WHERE document_id IN ({placeholders})"
        params = tuple(doc_ids)
    with _conn(db) as conn:
        cur = conn.cursor()
        cur.execute(sql, params)
        return cur.fetchall()


def insert_resolved_relationship_mentions(
    db: DatabaseClient,
    rows: List[Tuple[str, str, str, Optional[int], Optional[str], Optional[int]]],
) -> None:
    """Insert mention provenance rows; uniqueness on (resolved_rel_id, relationship_id) avoids duplicates."""
    sql = (
        "INSERT INTO resolved_relationship_mentions (resolved_rel_id, relationship_id, document_id, chunk_id, context, page)"
        " VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(resolved_rel_id, relationship_id) DO NOTHING"
    )
    with _conn(db) as conn:
        cur = conn.cursor()
        if rows:
            cur.executemany(sql, rows)
        conn.commit()


def upsert_resolved_relationships_base(
    db: DatabaseClient,
    rows: List[Tuple[str, str, str, str, Optional[str], Optional[str]]],
) -> None:
    """Ensure resolved_relationships rows exist for (subject, predicate, object); update first/last seen."""
    sql = (
        "INSERT INTO resolved_relationships (resolved_rel_id, subject_resolved_id, predicate, object_resolved_id, first_seen_at, last_seen_at)"
        " VALUES (?, ?, ?, ?, ?, ?)"
        " ON CONFLICT(resolved_rel_id) DO UPDATE SET"
        "   last_seen_at = CASE"
        "     WHEN excluded.last_seen_at > COALESCE(resolved_relationships.last_seen_at, excluded.last_seen_at)"
        "     THEN excluded.last_seen_at ELSE resolved_relationships.last_seen_at END"
    )
    with _conn(db) as conn:
        cur = conn.cursor()
        if rows:
            cur.executemany(sql, rows)
        conn.commit()


def recompute_resolved_relationship_counts(db: DatabaseClient, rel_ids: List[str]) -> None:
    """Recompute weight and doc_count from mention provenance to keep idempotency."""
    if not rel_ids:
        return
    placeholders = ",".join(["?"] * len(rel_ids))
    with _conn(db) as conn:
        cur = conn.cursor()
        # Update weight and doc_count from mentions per resolved_rel_id
        cur.execute(
            f"""
            UPDATE resolved_relationships
            SET weight = (
                SELECT COUNT(*) FROM resolved_relationship_mentions m
                WHERE m.resolved_rel_id = resolved_relationships.resolved_rel_id
            ),
                doc_count = (
                SELECT COUNT(DISTINCT m.document_id) FROM resolved_relationship_mentions m
                WHERE m.resolved_rel_id = resolved_relationships.resolved_rel_id
            )
            WHERE resolved_rel_id IN ({placeholders})
            """,
            tuple(rel_ids),
        )
        conn.commit()


def fetch_resolved_graph_snapshot(db: DatabaseClient, doc_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    """Assemble a GraphSnapshot-like payload from resolved tables.

    If doc_ids is provided, include only nodes/edges supported by at least one mention in those documents.
    """
    import sqlite3
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    with _conn(db) as conn:
        cur = conn.cursor()

        # Edges first (optionally filtered by doc_ids via mentions)
        if doc_ids:
            placeholders = ",".join(["?"] * len(doc_ids))
            cur.execute(
                f"""
                SELECT DISTINCT rr.resolved_rel_id, rr.subject_resolved_id, rr.predicate, rr.object_resolved_id,
                                rr.weight, rr.doc_count
                FROM resolved_relationships rr
                JOIN resolved_relationship_mentions m ON m.resolved_rel_id = rr.resolved_rel_id
                WHERE m.document_id IN ({placeholders})
                """,
                tuple(doc_ids),
            )
        else:
            cur.execute(
                "SELECT resolved_rel_id, subject_resolved_id, predicate, object_resolved_id, weight, doc_count FROM resolved_relationships"
            )
        edge_rows = cur.fetchall()
        from datetime import datetime
        now = datetime.utcnow().isoformat()
        for row in edge_rows:
            edges.append(
                {
                    "id": row[0],
                    "source": row[1],
                    "predicate": row[2],
                    "target": row[3],
                    "weight": row[4],
                    "docCount": row[5],
                    "createdAt": now,
                    "updatedAt": now,
                }
            )

        # Nodes: if filtered, only include nodes that appear in selected edges; otherwise include all canonicals
        node_ids_needed: Optional[set[str]] = None
        if doc_ids:
            node_ids_needed = set()
            for e in edges:
                node_ids_needed.add(e["source"])  # type: ignore[index]
                node_ids_needed.add(e["target"])  # type: ignore[index]

        # Precompute document sets per resolved_id for node visibility in UI filters
        doc_sets: Dict[str, set] = {}
        if doc_ids:
            # Limit doc sets to provided doc_ids
            placeholders = ",".join(["?"] * len(doc_ids))
            cur.execute(
                f"SELECT resolved_id, document_id FROM entity_resolution_map WHERE document_id IN ({placeholders})",
                tuple(doc_ids),
            )
        else:
            cur.execute("SELECT resolved_id, document_id FROM entity_resolution_map")
        for rid, did in cur.fetchall():
            if not did:
                continue
            doc_sets.setdefault(rid, set()).add(did)

        if node_ids_needed:
            placeholders = ",".join(["?"] * len(node_ids_needed))
            cur.execute(
                f"""
                SELECT resolved_id, primary_name, type, category, mention_count, doc_count
                FROM resolved_entities
                WHERE resolved_id IN ({placeholders})
                """,
                tuple(node_ids_needed),
            )
        else:
            cur.execute(
                "SELECT resolved_id, primary_name, type, category, mention_count, doc_count FROM resolved_entities"
            )
        for row in cur.fetchall():
            rid = row[0]
            nodes.append(
                {
                    "id": rid,
                    "label": row[1],
                    "type": row[2] or row[3] or "concept",
                    "description": row[3],
                    "mentionCount": row[4],
                    "docCount": row[5],
                    "documents": sorted(list(doc_sets.get(rid, set()))),
                    "triples": [],
                    "createdAt": now,
                    "updatedAt": now,
                }
            )

    return {"nodes": nodes, "edges": edges}
