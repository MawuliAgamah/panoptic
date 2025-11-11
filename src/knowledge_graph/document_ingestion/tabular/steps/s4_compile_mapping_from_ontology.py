"""Step that generates a MappingSpec from an ontology and CSV headers.

This implements the same heuristics used in the agent's auto pipeline:
 - Choose a main entity whose key appears in headers or has most outgoing rels
 - For relationships, map to CSV columns matching entity names/keys
 - For dimension entities without a clear key, create a synthetic slug key
"""

from __future__ import annotations

import logging
import json
from typing import Dict, Any, List, Tuple
from ...document_pipeline import DocumentPipelineContext, PipelineStep

logger = logging.getLogger("knowledgeAgent.pipeline.csv.generate_mapping")


def _headers_lc(profile) -> List[str]:
    try:
        return [str(h).strip().lower() for h in (profile.headers_original or [])]
    except Exception:
        return []


def _to_snake(name: str) -> str:
    import re
    s = re.sub(r"[^A-Za-z0-9]+", "_", name or "").strip("_")
    return s.lower()


def _norm_headers(headers: List[str]) -> Tuple[List[str], Dict[str, str]]:
    norm = {h.lower(): h for h in headers}
    return [h.lower() for h in headers], norm


def _normalize_ontology(ont: Dict[str, Any]) -> Dict[str, Any]:
    entities = ont.get("entities") if isinstance(ont, dict) else None
    relationships = (ont.get("relationships") if isinstance(ont, dict) else None) or []
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
    # Ensure each entity has name and key
    for e in ents:
        e.setdefault("name", "Entity")
        k = e.get("key")
        if isinstance(k, dict):
            pass
        elif isinstance(k, str):
            e["key"] = k
        else:
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
                import re as _re
                m = _re.split(r"\s*(?:->|→|\-|\|)\s*", r)
                if len(m) >= 2:
                    rel_list.append({"source": m[0], "predicate": "related_to", "target": m[-1]})
    elif isinstance(relationships, dict):
        rel_list = [relationships]
    return {"entities": ents, "relationships": rel_list}


def _pick_main_entity(entities: List[Dict[str, Any]], headers_lc: List[str], rels: List[Dict[str, Any]]) -> Tuple[str, str]:
    from collections import Counter
    cnt = Counter()
    for r in rels:
        src = str(r.get("source", "")).lower()
        cnt[src] += 1
    if cnt:
        top = max(cnt.items(), key=lambda x: x[1])[0]
        e = next((e for e in entities if str(e.get("name", "")).lower() == top), None)
        if e:
            k = e.get("key")
            if isinstance(k, str) and k.lower() in headers_lc:
                return str(e.get("name")), k
            return str(e.get("name")), (headers_lc[0] if headers_lc else "id")
    for e in entities:
        name = str(e.get("name", "")).strip() or "Entity"
        key = e.get("key")
        key_name = key if isinstance(key, str) else None
        if key_name and key_name.lower() in headers_lc:
            return name, key_name
    id_hdr = next((h for h in headers_lc if h.endswith("_id")), None)
    if entities and id_hdr:
        return str(entities[0].get("name", "Entity")), id_hdr
    return (str(entities[0].get("name", "Entity")) if entities else "Entity", (headers_lc[0] if headers_lc else "id"))


def _match_target_to_header(target_entity: str, headers_lc: List[str], attrs: List[Dict[str, Any]]) -> str | None:
    cand = _to_snake(target_entity)
    if cand in headers_lc:
        return cand
    compact = cand.replace("_", "")
    for h in headers_lc:
        if h.replace("_", "") == compact:
            return h
    # Look for *_id or columns that reference target's key
    target_key = None
    for a in attrs or []:
        if isinstance(a, dict) and str(a.get("name", "")).endswith("_id"):
            target_key = str(a.get("name")).lower()
            break
    if target_key and target_key in headers_lc:
        return target_key
    for h in headers_lc:
        if h.endswith("_id") and cand in h:
            return h
    return None


class GenerateMappingFromOntologyStep(PipelineStep):
    name = "generate_mapping_from_ontology"

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return self.enabled and hasattr(context, "ontology_spec") and bool(getattr(context, "ontology_spec", None))

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        ontology: Dict[str, Any] = getattr(context, "ontology_spec", {}) or {}
        profile = getattr(context, "csv_profile", None)
        headers = getattr(profile, "headers_original", []) if profile else []
        headers_lc, norm_map = _norm_headers(headers)

        ont = _normalize_ontology(ontology)
        ents = ont.get("entities", [])
        rels = ont.get("relationships", [])

        # Choose main entity
        main_ent_name, main_key = _pick_main_entity(ents, headers_lc, rels)

        warnings: List[str] = []
        mapping_entities: Dict[str, Any] = {}
        for e in ents:
            name = str(e.get("name") or "Entity").strip() or "Entity"
            key_str = (e.get("key") or e.get("primary_key") or "").strip()
            key_spec: Dict[str, Any] = {}
            if key_str:
                if key_str.lower() in headers_lc:
                    key_spec = {"column": norm_map.get(key_str.lower(), key_str)}
                else:
                    warnings.append(f"entity '{name}': key '{key_str}' not found in headers")
            elif name != main_ent_name:
                # Create synthetic slug key for dimensions without explicit key
                # It will be computed downstream; here we leave it empty to avoid false references
                key_spec = {}
            mapping_entities[name] = {"key": key_spec, "attributes": []}

        edges: List[Dict[str, Any]] = []
        for r in rels:
            pred = (r.get("predicate") or r.get("relation") or r.get("label") or "related_to").strip() or "related_to"
            src_ent = str(r.get("source") or "").strip() or main_ent_name
            tgt_ent = str(r.get("target") or "").strip()

            # Heuristically find join columns if not specified
            join = r.get("join_columns") or {}
            sc = (join.get("source_col") or "").strip() if isinstance(join, dict) else ""
            tc = (join.get("target_col") or "").strip() if isinstance(join, dict) else ""
            if not sc:
                sc_guess = _match_target_to_header(tgt_ent, headers_lc, next((e.get("attributes") for e in ents if str(e.get("name",""))==tgt_ent), []))
                if sc_guess:
                    sc = norm_map.get(sc_guess, sc_guess)
            if not tc:
                # Use target's own key if present
                tgt = next((e for e in ents if str(e.get("name", "")).strip() == tgt_ent), None)
                tgt_key = (tgt.get("key") if isinstance(tgt, dict) else None) if tgt else None
                if isinstance(tgt_key, str) and tgt_key.lower() in headers_lc:
                    tc = norm_map.get(tgt_key.lower(), tgt_key)

            source_by = {"column": sc} if sc else {}
            target_by = {"column": tc} if tc else {}
            edges.append({
                "predicate": pred,
                "source": {"entity": src_ent, "by": source_by},
                "target": {"entity": tgt_ent, "by": target_by},
            })

        mapping: Dict[str, Any] = {"entities": mapping_entities, "edges": edges, "options": {"null_policy": "skip"}}

        setattr(context, "mapping_spec", mapping)
        context.results[self.name] = {"entities": len(mapping_entities), "edges": len(edges), "warnings": warnings}
        # Pretty-print mapping for observability (could be large; consider DEBUG in prod)
 
        logger.info("%s: mapping compiled: %s", getattr(context.document, 'id', '-'), json.dumps(mapping, indent=2))

        return context
