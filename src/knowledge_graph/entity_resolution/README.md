# Entity Resolution Module — Design and Plan

This module deduplicates entities across documents into canonical “resolved” entities and remaps relationships to those canonicals while preserving per‑mention provenance. It is designed to be incremental and extensible: start with exact normalized matching, then evolve to fuzzy/embedding/LLM.

## Goals
- Deduplicate entity mentions into canonical entities.
- Remap relationships to canonical IDs; keep provenance (doc/chunk/page/context).
- Idempotent and incremental: safe to re‑run as new docs arrive.
- Modular design with clear extension points for better matching.

## Folder Structure
src/knowledge_graph/entity_resolution/
├── __init__.py
├── models.py              # Dataclasses: ResolvedEntity, EntityMention, ResolvedRelation, ResolutionStats
├── normalize.py           # normalize_name(name: str, type: str) -> str
│                          # Type-aware helpers (person/org/location) — optional toggles in v1
├── matchers.py            # ExactNormalizedMatcher (v1): match on normalized key
│                          # Stubs: FuzzyTokenMatcher, EmbeddingMatcher (future)
├── cluster.py             # block_mentions(mentions) -> dict[key, mentions]
│                          # choose_primary_name(mentions) -> str
│                          # build_resolved_id(normalized_key, type) -> str (e.g., SHA1-based)
├── persist.py             # ensure_schema(db) — create tables if not exist
│                          # Upserts for resolved_entities, entity_resolution_map, resolved_relationships
│                          # Inserts for resolved_relationship_mentions
├── service.py             # EntityResolutionService orchestrates load → resolve → remap → persist
│                          # Public method: resolve(filter: ResolutionFilter, mode: 'incremental'|'full') -> ResolutionStats

## Database Schema (New Tables)
Keep existing `entities` and `relationships` unchanged. Add the following:

1) `resolved_entities`
- `resolved_id` TEXT PRIMARY KEY
- `primary_name` TEXT NOT NULL
- `normalized_key` TEXT NOT NULL  (e.g., "type|normalized_name")
- `type` TEXT, `category` TEXT
- `mention_count` INTEGER DEFAULT 0
- `doc_count` INTEGER DEFAULT 0
- `created_at` TEXT DEFAULT CURRENT_TIMESTAMP
- `updated_at` TEXT DEFAULT CURRENT_TIMESTAMP
- UNIQUE(`normalized_key`, `type`)

2) `entity_resolution_map`
- `entity_id` TEXT PRIMARY KEY  (original entity)
- `resolved_id` TEXT NOT NULL
- `strategy` TEXT NOT NULL DEFAULT 'exact'
- `confidence` REAL NOT NULL DEFAULT 1.0
- `normalized_key` TEXT NOT NULL
- `created_at` TEXT DEFAULT CURRENT_TIMESTAMP

3) `resolved_relationships`
- `resolved_rel_id` TEXT PRIMARY KEY  (hash of subject|predicate|object)
- `subject_resolved_id` TEXT NOT NULL
- `predicate` TEXT NOT NULL
- `object_resolved_id` TEXT NOT NULL
- `weight` INTEGER NOT NULL DEFAULT 0  (#mentions)
- `doc_count` INTEGER NOT NULL DEFAULT 0
- `first_seen_at` TEXT, `last_seen_at` TEXT
- UNIQUE(`subject_resolved_id`, `predicate`, `object_resolved_id`)

4) `resolved_relationship_mentions`
- `resolved_rel_id` TEXT NOT NULL
- `relationship_id` TEXT NOT NULL  (original)
- `document_id` TEXT, `chunk_id` TEXT
- `context` TEXT, `page` INTEGER
- `created_at` TEXT DEFAULT CURRENT_TIMESTAMP

Indexes recommended on `entity_resolution_map.resolved_id`, `resolved_relationships(subject_resolved_id, object_resolved_id)`, and `resolved_entities.normalized_key`.

## Core Algorithm (v1: Exact Matching)
1) Load mentions
- From `entities` table: `entity_id, name, type, category, document_id, chunk_id` (+ page if available).

2) Normalize and block
- Normalize name: lowercase, Unicode NFKD fold, strip, collapse whitespace, remove punctuation (keep alphanumerics/spaces). Optional type‑aware tweaks:
  - Person: drop honorifics, middle initials; reorder “Last, First” → “First Last”.
  - Org: drop suffixes (inc, ltd, corp, llc); normalize `&` → `and`.
  - Location: expand common abbreviations (small dictionary).
- `normalized_key = f"{type}|{normalized_name}"` prevents cross‑type merges.

3) Create/Upsert canonical entities
- Group mentions by `(normalized_key, type)`.
- `resolved_id = 'res::' + sha1(type + '|' + normalized_name)[:16]` (deterministic).
- `primary_name` = most frequent original `name` (tie breaker: longest or earliest seen).
- `mention_count` = group size; `doc_count` = distinct(document_id).
- Upsert into `resolved_entities` (increment counts, set `updated_at`).

4) Map mentions → canonicals
- Upsert into `entity_resolution_map(entity_id → resolved_id)` with `strategy='exact'`, `confidence=1.0`.

5) Remap relationships
- Join `relationships` with `entity_resolution_map` twice (source/target).
- Compute `resolved_rel_id = sha1(subject_resolved_id + '|' + predicate + '|' + object_resolved_id)`.
- Upsert into `resolved_relationships`:
  - increment `weight`, update `doc_count`, set `first_seen_at`/`last_seen_at`.
- Insert provenance rows into `resolved_relationship_mentions` with `relationship_id`, `document_id`, `chunk_id`, `context`, `page`.

## Service API & Flow
```python
class ResolutionFilter(TypedDict, total=False):
    doc_ids: list[str]
    tags: list[str]
    start_at: str  # ISO
    end_at: str    # ISO

class EntityResolutionService:
    def __init__(self, db_client):
        ...

    def resolve(self, filter: ResolutionFilter | None = None, mode: str = 'incremental') -> ResolutionStats:
        ensure_schema(db)
        mentions = self.load_mentions(db, filter)
        blocks = block_mentions(mentions)  # by normalized_key
        resolved_entities, mapping = self.resolve_entities(blocks)
        upsert_resolved_entities(db, resolved_entities)
        upsert_entity_resolution_map(db, mapping)
        resolved_edges, rel_mentions = self.remap_relationships(db, mapping, filter)
        upsert_resolved_relationships(db, resolved_edges)
        insert_resolved_rel_mentions(db, rel_mentions)
        return stats
```

## Integration Points
- Backend: call `EntityResolutionService.resolve(...)` after new documents are processed, or on a schedule.
- Frontend: fetch resolved graph instead of raw:
  - Nodes: `SELECT resolved_id, primary_name, type, category, mention_count FROM resolved_entities WHERE …`.
  - Edges: `SELECT subject_resolved_id AS source, predicate, object_resolved_id AS target, weight FROM resolved_relationships WHERE …`.
  - Provenance: `SELECT * FROM resolved_relationship_mentions WHERE resolved_rel_id = ?`.

## Incremental Runs
- For new documents, resolve only mentions from those docs:
  - Compute normalized keys, upsert canonicals/mappings.
  - Remap only the new relationships and upsert/aggregate in `resolved_relationships`.
- Idempotency is guaranteed via unique constraints and deterministic IDs.

## Logging & Metrics
- INFO: mentions_loaded, blocks, resolved_entities_upserted, mapped_mentions, edges_upserted, rel_mentions_inserted, elapsed by phase.
- DEBUG: sample largest clusters, top aliases, example resolved edges with weights.
- ERROR: DB upsert failures — log and continue batch where safe.

## Testing Strategy
- Unit: normalization rules, primary name selection, resolved_id hashing, relation deduplication/weights.
- Integration: two documents with overlapping entities → merged canonical + remapped relations; provenance retained.
- Idempotency: running resolve twice yields stable counts (no dupes).

## Performance Notes
- Prefer set‑based SQL upserts (JOIN map twice for relationships).
- Batch by doc_ids or time window for large datasets.
- Use transactions per phase (entities → map → relations) to keep consistent.

## Extensibility Roadmap
- v2: `FuzzyTokenMatcher` (e.g., rapidfuzz) for near‑duplicates.
- v3: `EmbeddingMatcher` with cosine similarity on names (and short context).
- v4: Type/ontology constraints to prevent cross‑type merges.
- v5: Graph/contextual signals; v6: LLM adjudication for tough cases.

