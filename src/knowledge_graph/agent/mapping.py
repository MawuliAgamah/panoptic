"""Compile a first-pass mapping.json from ontology + CSV headers.

Heuristics:
- Choose a main entity whose key appears as a CSV header (e.g., person_id).
- For relationships from the main entity to target entities, map to CSV columns
  with similar names (exact lower match, snake-case match, or attribute hint).
- Dimension entity keys default to slug(column) with a prefix built from entity name.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Tuple


logger = logging.getLogger("knowledgeAgent.agent.mapping")


def _to_snake(name: str) -> str:
    s = re.sub(r"[^A-Za-z0-9]+", "_", name or "").strip("_")
    return s.lower()


def _norm_headers(headers: List[str]) -> Tuple[List[str], Dict[str, str]]:
    norm = {h.lower(): h for h in headers}
    return [h.lower() for h in headers], norm


def _normalize_ontology(ont: Dict[str, Any]) -> Dict[str, Any]:
    entities = ont.get("entities") if isinstance(ont, dict) else None
    relationships = (ont.get("relationships") if isinstance(ont, dict) else None) or []
    # Entities may arrive as a dict keyed by name or an array
    ents: List[Dict[str, Any]] = []
    if isinstance(entities, dict):
        for name, spec in entities.items():
            s = spec.copy() if isinstance(spec, dict) else {}
            s.setdefault("name", name)
            ents.append(s)
    elif isinstance(entities, list):
        ents = entities
    else:
        ents = []
    # Ensure each entity has name and key (string if possible)
    for e in ents:
        e.setdefault("name", "Entity")
        k = e.get("key")
        # accept either string key or nested key spec
        if isinstance(k, dict):
            # keep as-is
            pass
        elif isinstance(k, str):
            e["key"] = k
        else:
            # attempt to infer *_id attribute as key
            attrs = e.get("attributes") or []
            key_attr = next((a.get("name") for a in attrs if isinstance(a, dict) and str(a.get("name", "")).endswith("_id")), None)
            if key_attr:
                e["key"] = key_attr
    # Normalize relationships to list[dict]
    rel_list: List[Dict[str, Any]] = []
    if isinstance(relationships, list):
        for r in relationships:
            if isinstance(r, dict):
                rel_list.append(r)
            elif isinstance(r, str):
                # Best-effort parse "Source predicate Target" or skip
                # Very loose heuristic: split by '->' or ' - ' or '|' etc.
                m = re.split(r"\s*(?:->|→|\-|\|)\s*", r)
                if len(m) >= 2:
                    rel_list.append({"source": m[0], "predicate": "related_to", "target": m[-1]})
                else:
                    # fallback skip
                    continue
            else:
                continue
    elif isinstance(relationships, dict):
        rel_list = [relationships]
    else:
        rel_list = []

    return {"entities": ents, "relationships": rel_list}


def _pick_main_entity(entities: List[Dict[str, Any]], headers_lc: List[str], rels: List[Dict[str, Any]]) -> Tuple[str, str]:
    # Prefer entity with most outgoing relationships
    from collections import Counter
    cnt = Counter()
    for r in rels:
        src = str(r.get("source", "")).lower()
        cnt[src] += 1
    if cnt:
        top = max(cnt.items(), key=lambda x: x[1])[0]
        e = next((e for e in entities if str(e.get("name", "")).lower() == top), None)
        if e:
            # Use explicit key if present
            k = e.get("key")
            if isinstance(k, str) and k.lower() in headers_lc:
                return str(e.get("name")), k
            # If composite key phrase, handle later; temporarily return first header
            return str(e.get("name")), (headers_lc[0] if headers_lc else "id")
    # Else: entity whose key appears in headers
    for e in entities:
        name = str(e.get("name", "")).strip() or "Entity"
        key = e.get("key")
        key_name = key if isinstance(key, str) else None
        if key_name and key_name.lower() in headers_lc:
            return name, key_name
    # Fallback: header *_id
    id_hdr = next((h for h in headers_lc if h.endswith("_id")), None)
    if entities and id_hdr:
        return str(entities[0].get("name", "Entity")), id_hdr
    # Last resort
    return (str(entities[0].get("name", "Entity")) if entities else "Entity", (headers_lc[0] if headers_lc else "id"))


def _match_target_to_header(target_entity: str, headers_lc: List[str], person_attrs: List[str]) -> str | None:
    # Exact match on snake-case target name (e.g., EmploymentStatus -> employment_status)
    cand = _to_snake(target_entity)
    if cand in headers_lc:
        return cand
    # Remove underscores and try contains match: region vs us_region
    compact = cand.replace("_", "")
    for h in headers_lc:
        if compact in h.replace("_", ""):
            return h
    # Check if Person attributes contain a similarly named column
    for a in person_attrs:
        a_snake = _to_snake(a)
        if a_snake in headers_lc:
            # Only accept when attribute name is substring of target entity name or vice versa
            if a_snake in cand or cand in a_snake:
                return a_snake
    # Synonyms for common targets
    SYN = {
        "customer": ["segment", "customer"],
        "date": ["date"],
        "product": ["product"],
        "country": ["country"],
        "transaction": ["transaction", "txn", "row_id"],
    }
    t = target_entity.lower()
    for key, alts in SYN.items():
        if key in t:
            for alt in alts:
                if alt in headers_lc:
                    return alt
    return None


def compile_mapping_from_ontology(ontology: Dict[str, Any], csv_headers: List[str]) -> Tuple[Dict[str, Any], List[str]]:
    """Produce a first-pass mapping.json and warnings from ontology + CSV headers."""
    warnings: List[str] = []
    ont = _normalize_ontology(ontology)
    ents: List[Dict[str, Any]] = ont.get("entities", [])
    rels: List[Dict[str, Any]] = ont.get("relationships", [])
    headers_lc, orig = _norm_headers(csv_headers)

    if not ents:
        return {"entities": {}, "edges": [], "options": {"dedupe": True, "null_policy": "skip"}}, ["No entities in ontology"]

    main_name, main_key_hdr = _pick_main_entity(ents, headers_lc, rels)
    if main_key_hdr not in headers_lc:
        warnings.append(f"Main key column '{main_key_hdr}' not found; results may be invalid")
    main_key_hdr_orig = orig.get(main_key_hdr, main_key_hdr)

    # Collect attributes for the main entity (hint for matching)
    person_attrs = []
    for e in ents:
        if str(e.get("name", "")).strip().lower() == main_name.lower():
            attrs = e.get("attributes") or []
            for a in attrs:
                nm = str(a.get("name", ""))
                if nm:
                    person_attrs.append(nm)

    # Build mapping.entities
    mapping_entities: Dict[str, Any] = {}
    # Main entity key
    # Build main entity key; support composite key phrases
    main_ent = next((e for e in ents if str(e.get("name", "")).lower() == main_name.lower()), {})
    key_field = main_ent.get("key")
    if isinstance(key_field, str) and key_field.lower().startswith("composite key"):
        # Extract candidate columns from the phrase
        # e.g., "Composite key using Date and Product"
        cols = []
        m = re.findall(r"[A-Za-z0-9_ ]+", key_field)
        # Heuristic: choose headers that appear in phrase
        for h in headers_lc:
            orig_h = orig[h]
            if orig_h and orig_h.lower() in key_field.lower():
                cols.append(orig_h)
        # Fallback if not found
        if not cols:
            cols = [orig.get(main_key_hdr, main_key_hdr)]
        # Build template
        tmpl = f"{_to_snake(main_name)}:" + "|".join([f"{{{c}}}" for c in cols])
        transforms = {c: ("slug" if c.lower() != "date" else "trim") for c in cols}
        mapping_entities[main_name] = {"key": {"template": tmpl, "transforms": transforms}}
    else:
        mapping_entities[main_name] = {
            "key": {"prefix": f"{_to_snake(main_name)}:", "column": main_key_hdr_orig}
        }

    # For each relationship whose source == main entity, try to map to a header
    edges = []
    for r in rels:
        if not isinstance(r, dict):
            warnings.append(f"Skipping non-object relationship entry: {r!r}")
            continue
        # Accept both strings and nested objects for source/target
        src_val = r.get("source")
        tgt_val = r.get("target")
        if isinstance(src_val, dict):
            src = str(src_val.get("name") or src_val.get("entity") or "")
        else:
            src = str(src_val or "")
        if isinstance(tgt_val, dict):
            tgt = str(tgt_val.get("name") or tgt_val.get("entity") or "")
        else:
            tgt = str(tgt_val or "")
        pred = r.get("predicate") or r.get("relation") or r.get("label") or "related_to"
        if not src or not tgt:
            continue
        if src.lower() != main_name.lower():
            continue
        # Find a CSV column that likely represents the target
        match_hdr = _match_target_to_header(tgt, headers_lc, person_attrs)
        if not match_hdr:
            warnings.append(f"Could not match relationship target '{tgt}' to any CSV column")
            continue
        hdr_orig = orig.get(match_hdr, match_hdr)
        # Dimension entity spec (slugged key)
        mapping_entities[tgt] = {
            "key": {"prefix": f"{_to_snake(tgt)}:", "column": hdr_orig, "transform": "slug"}
        }
        edges.append({
            "predicate": pred,
            "source": {"entity": main_name},
            "target": {"entity": tgt}
        })

    mapping = {
        "entities": mapping_entities,
        "edges": edges,
        "options": {"dedupe": True, "null_policy": "skip"}
    }
    logger.info(
        "[mapping] compiled main=%s key=%s dims=%d edges=%d",
        main_name,
        main_key_hdr_orig,
        len(mapping_entities) - 1,
        len(edges),
    )
    return mapping, warnings


__all__ = ["compile_mapping_from_ontology"]
