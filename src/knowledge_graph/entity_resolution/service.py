from __future__ import annotations

import logging
from typing import Dict, List, Tuple, Optional
from collections import defaultdict

# from ..persistence.sqlite.sql_lite import SqlLite
from .models import (
    ResolutionFilter,
    EntityMention,
    ResolvedEntity,
    ResolutionStats,
)
from .normalize import normalize_name
from .cluster import block_mentions, build_resolved_entities, build_key, build_resolved_id
from .matchers import ExactNormalizedMatcher
from . import persist


logger = logging.getLogger(__name__)


class EntityResolutionService:
    """Entity resolution orchestrator.

    Usage:
        svc = EntityResolutionService(db_client)
        stats = svc.resolve({"doc_ids": [..]}, mode="incremental")
    """

    def __init__(self) -> None:
        pass 

    def resolve(self, filter: Optional[ResolutionFilter] = None, mode: str = "incremental") -> ResolutionStats:
        persist.ensure_schema(self.db)
        filt = filter or {}
        doc_ids = filt.get("doc_ids") if isinstance(filt, dict) else None

        # 1) Load mentions
        mentions = persist.fetch_mentions(self.db, doc_ids=doc_ids)
        stats = ResolutionStats(mentions_loaded=len(mentions))
        if not mentions:
            logger.info("[ER] No mentions loaded (filter=%s)", filt)
            return stats

        # 2) Normalize + block
        matcher = ExactNormalizedMatcher()
        mention_pairs = matcher.transform(mentions)
        blocks = block_mentions(mention_pairs)
        stats.blocks = len(blocks)

        # 3) Build resolved entities + mapping
        resolved_entities = build_resolved_entities(blocks)
        # Build mapping rows: (entity_id, resolved_id, normalized_key, document_id, strategy, confidence)
        mappings: List[Tuple[str, str, str, str, str, float]] = []
        for key, group in blocks.items():
            rid = build_resolved_id(key)
            for m in group:
                mappings.append((m.entity_id, rid, key, m.document_id, "exact", 1.0))

        # 4) Persist resolved entities + mapping
        up1 = persist.upsert_resolved_entities(self.db, resolved_entities)
        up2 = persist.upsert_entity_resolution_map(self.db, mappings)
        stats.resolved_entities_upserted = up1
        stats.mapped_mentions = up2

        # 5) Remap relationships
        self._remap_relationships(doc_ids, stats)

        # 6) Recompute resolved entity counts from mapping (idempotent)
        self._recompute_resolved_entity_counts()

        logger.info(
            "[ER] DONE: mentions=%d blocks=%d canonicals=%d mapped=%d edges=%d rel_mentions=%d",
            stats.mentions_loaded,
            stats.blocks,
            stats.resolved_entities_upserted,
            stats.mapped_mentions,
            stats.edges_upserted,
            stats.rel_mentions_inserted,
        )
        return stats

    def _remap_relationships(self, doc_ids: Optional[List[str]], stats: ResolutionStats) -> None:
        # Load relationships (optionally filtered by docs)
        rel_rows = persist.fetch_relationships(self.db, doc_ids=doc_ids)
        if not rel_rows:
            return

        # Build a mapping of entity_id -> resolved_id
        entity_to_resolved: Dict[str, str] = self._fetch_entity_map()

        # Prepare base upserts and mention inserts
        base_rows: List[Tuple[str, str, str, str, Optional[str], Optional[str]]] = []
        mention_rows: List[Tuple[str, str, str, Optional[int], Optional[str], Optional[int]]] = []
        touched_rel_ids: List[str] = []

        import hashlib
        for (relationship_id, src_eid, tgt_eid, predicate, context, document_id, chunk_id, created_at) in rel_rows:
            s_r = entity_to_resolved.get(src_eid)
            o_r = entity_to_resolved.get(tgt_eid)
            if not s_r or not o_r:
                # Skip if either side did not map yet
                continue
            rid_key = f"{s_r}|{predicate}|{o_r}"
            resolved_rel_id = hashlib.sha1(rid_key.encode("utf-8")).hexdigest()[:16]
            # Ensure base row
            base_rows.append((resolved_rel_id, s_r, predicate, o_r, created_at, created_at))
            # Mention provenance
            mention_rows.append((resolved_rel_id, relationship_id, document_id, chunk_id, context, None))
            touched_rel_ids.append(resolved_rel_id)

        if not base_rows:
            return

        persist.upsert_resolved_relationships_base(self.db, base_rows)
        persist.insert_resolved_relationship_mentions(self.db, mention_rows)
        persist.recompute_resolved_relationship_counts(self.db, list(set(touched_rel_ids)))
        stats.edges_upserted = len(set(touched_rel_ids))
        stats.rel_mentions_inserted = len(mention_rows)

    def _fetch_entity_map(self) -> Dict[str, str]:
        sql = "SELECT entity_id, resolved_id FROM entity_resolution_map"
        import sqlite3
        mapping: Dict[str, str] = {}
        with persist._conn(self.db) as conn:  # type: ignore[attr-defined]
            cur = conn.cursor()
            cur.execute(sql)
            for eid, rid in cur.fetchall():
                mapping[eid] = rid
        return mapping

    def _recompute_resolved_entity_counts(self) -> None:
        # Update mention_count and doc_count from entity_resolution_map for idempotency
        with persist._conn(self.db) as conn:  # type: ignore[attr-defined]
            cur = conn.cursor()
            cur.execute(
                """
                UPDATE resolved_entities
                SET mention_count = (
                    SELECT COUNT(*) FROM entity_resolution_map m
                    WHERE m.resolved_id = resolved_entities.resolved_id
                ),
                    doc_count = (
                    SELECT COUNT(DISTINCT m.document_id) FROM entity_resolution_map m
                    WHERE m.resolved_id = resolved_entities.resolved_id
                ),
                    updated_at = CURRENT_TIMESTAMP
                """
            )
            conn.commit()

