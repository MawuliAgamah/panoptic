"""Lightweight entity resolution for KG payloads (entities + relations).

Given a KG payload of the form:
  { entities: ["prefix:value", ...], relations: [[s, p, t], ...] }

This module canonicalizes node IDs by prefix and normalized value, merges
duplicates, and rewrites the relations accordingly.

It is intentionally heuristic and fast for client-side / pilot use. Your
production ER service can replace this once wired.
"""

from __future__ import annotations

from typing import Dict, Any, Tuple, Iterable
import logging
import re

from .normalizers import slug, trim, to_lower


logger = logging.getLogger("knowledgeAgent.agent.er")


DEFAULT_PROTECTED_PREFIXES = {"txn", "transaction", "date"}


def _split_prefix(node_id: str) -> Tuple[str, str]:
    if not node_id:
        return ("", "")
    if ":" not in node_id:
        return ("node", node_id)
    a, b = node_id.split(":", 1)
    return (a or "node", b)


def _canonical_value(prefix: str, value: str, synonyms: Dict[str, Dict[str, str]] | None) -> str:
    v = trim(value)
    v = re.sub(r"\s+", " ", v)
    v_lc = to_lower(v)
    # Apply prefix-specific synonyms if provided
    syn = (synonyms or {}).get(prefix.lower()) or {}
    canon = syn.get(v_lc)
    if canon:
        v = canon
    # Slug for stability
    v_slug = slug(v)
    return v_slug


def resolve_entities(
    kg: Dict[str, Any],
    *,
    protected_prefixes: Iterable[str] | None = None,
    synonyms: Dict[str, Dict[str, str]] | None = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Resolve duplicate nodes by canonicalizing IDs per prefix.

    Returns (resolved_kg, stats).
    """
    entities = list(kg.get("entities", []) or [])
    relations = list(kg.get("relations", []) or [])

    protected = set((protected_prefixes or DEFAULT_PROTECTED_PREFIXES))

    # Build canonical mapping
    canonical_by_key: Dict[Tuple[str, str], str] = {}
    old_to_new: Dict[str, str] = {}
    by_prefix_merged: Dict[str, int] = {}

    for eid in entities:
        pref, val = _split_prefix(str(eid))
        if pref.lower() in protected:
            old_to_new[eid] = eid
            continue

        vcanon = _canonical_value(pref, val, synonyms)
        key = (pref, vcanon)
        if key in canonical_by_key:
            # Existing canonical id
            cid = canonical_by_key[key]
            old_to_new[eid] = cid
            by_prefix_merged[pref] = by_prefix_merged.get(pref, 0) + 1
        else:
            # Choose canonical id as f"{prefix}:{vcanon}"
            cid = f"{pref}:{vcanon}" if vcanon else eid
            canonical_by_key[key] = cid
            old_to_new[eid] = cid

    # Rewrite entities/relations
    new_entities = set()
    for eid in entities:
        new_entities.add(old_to_new.get(eid, eid))

    new_relations = set()
    for s, p, t in relations:
        s2 = old_to_new.get(str(s), str(s))
        t2 = old_to_new.get(str(t), str(t))
        new_relations.add((s2, str(p), t2))

    resolved = {
        "entities": sorted(new_entities),
        "relations": [list(x) for x in sorted(new_relations)],
    }

    stats = {
        "input_nodes": len(entities),
        "resolved_nodes": len(new_entities),
        "input_edges": len(relations),
        "resolved_edges": len(new_relations),
        "merged_by_prefix": by_prefix_merged,
    }
    logger.info(
        "[er] nodes %d → %d, edges %d → %d, merges=%s",
        stats["input_nodes"], stats["resolved_nodes"], stats["input_edges"], stats["resolved_edges"], stats["merged_by_prefix"],
    )
    return resolved, stats


__all__ = ["resolve_entities"]


def _normalize_label_for_merge(node_id: str, *, ignore_prefix: bool = True) -> str:
    pref, val = _split_prefix(node_id)
    s = val if ignore_prefix else f"{pref}:{val}"
    s = trim(s)
    s = re.sub(r"\s+", " ", s)
    s = s.lower()
    # remove punctuation and separators for a simple, aggressive merge
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def resolve_entities_simple(
    kg: Dict[str, Any],
    *,
    ignore_prefix: bool = True,
    prune_isolates: bool = False,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Simpler ER: merge nodes whose normalized labels match exactly.

    - Normalization: lowercase, trim, collapse whitespace, drop punctuation.
    - If ignore_prefix is True (default), merges across prefixes (e.g., product:Amarilla and Amarilla).
    - Keeps all relationships; dedupes edges.
    - Optionally prunes isolates (nodes left with degree 0 after rewriting).
    """
    entities = list(kg.get("entities", []) or [])
    relations = list(kg.get("relations", []) or [])

    buckets: Dict[str, str] = {}
    old_to_new: Dict[str, str] = {}

    for eid in entities:
        key = _normalize_label_for_merge(str(eid), ignore_prefix=ignore_prefix)
        if not key:
            # keep as-is
            old_to_new[eid] = eid
            continue
        if key in buckets:
            old_to_new[eid] = buckets[key]
        else:
            # choose first-seen as canonical to preserve original id shape
            buckets[key] = str(eid)
            old_to_new[eid] = str(eid)

    # Rewrite
    new_relations = []
    for s, p, t in relations:
        s2 = old_to_new.get(str(s), str(s))
        t2 = old_to_new.get(str(t), str(t))
        new_relations.append([s2, str(p), t2])

    # Dedup edges
    rel_set = set()
    dedup_rel = []
    for s, p, t in new_relations:
        k = (s, p, t)
        if k in rel_set:
            continue
        rel_set.add(k)
        dedup_rel.append([s, p, t])

    # New entities: canonicals actually referenced, plus any canon from buckets with degree 0 if not pruning
    referenced = set()
    for s, _, t in dedup_rel:
        referenced.add(s)
        referenced.add(t)
    canon_set = set(buckets.values())
    if prune_isolates:
        new_entities = referenced
    else:
        new_entities = referenced | canon_set

    resolved = {"entities": sorted(new_entities), "relations": dedup_rel}
    stats = {
        "input_nodes": len(entities),
        "resolved_nodes": len(new_entities),
        "input_edges": len(relations),
        "resolved_edges": len(dedup_rel),
        "merged_buckets": len(buckets),
    }
    logger.info(
        "[er-simple] nodes %d → %d, edges %d → %d",
        stats["input_nodes"], stats["resolved_nodes"], stats["input_edges"], stats["resolved_edges"],
    )
    return resolved, stats

