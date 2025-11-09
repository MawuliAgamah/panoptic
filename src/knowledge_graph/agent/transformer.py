"""CSV → Knowledge Graph transformer using a minimal mapping spec.

Mapping JSON shape (minimal pilot):
{
  "entities": {
    "Person": {
      "key": {"prefix": "person:", "column": "person_id", "transform": null}
    },
    "Education": {
      "key": {"prefix": "education:", "column": "education", "transform": "slug"}
    }
  },
  "edges": [
    {
      "predicate": "has Education",
      "source": {"entity": "Person"},                  # uses entity key by default
      "target": {"entity": "Education"}                # uses entity key by default
    }
  ],
  "options": {"dedupe": true, "null_policy": "skip"}
}
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Iterable, Optional, Set, Tuple

from .tools import sniff_csv, read_rows
from .normalizers import REGISTRY as NORMALIZERS


logger = logging.getLogger("knowledgeAgent.agent.transformer")


def _apply_transform(value: Any, name: Optional[str]) -> str:
    if not name:
        return "" if value is None else str(value)
    fn = NORMALIZERS.get(name)
    return fn(value) if fn else ("" if value is None else str(value))


def _compute_entity_id(row: Dict[str, Any], key_spec: Dict[str, Any]) -> str:
    # Support either {column,prefix,transform} or {template,transforms}
    template = key_spec.get("template")
    if template:
        transforms = key_spec.get("transforms", {}) or {}
        # Replace {Field} placeholders with normalized values
        def repl(match):
            col = match.group(1)
            xf = transforms.get(col)
            return _apply_transform(row.get(col, ""), xf)
        import re
        value = re.sub(r"\{([^}]+)\}", repl, template)
        return value if value else ""
    else:
        prefix = key_spec.get("prefix", "")
        col = key_spec.get("column")
        xform = key_spec.get("transform")
        raw = row.get(col, "")
        norm = _apply_transform(raw, xform)
        return f"{prefix}{norm}" if norm else ""


def _entity_key_spec(entity_spec: Dict[str, Any]) -> Dict[str, Any]:
    key = entity_spec.get("key") or {}
    if not isinstance(key, dict):
        key = {}
    return key


def _resolve_node_id(row: Dict[str, Any], mapping: Dict[str, Any], which: Dict[str, Any]) -> str:
    # which: {entity: "Person"} or {entity: "Education", by: {prefix, column, transform}}
    entity_name = which.get("entity")
    entities = mapping.get("entities", {})
    e_spec = entities.get(entity_name, {}) if isinstance(entities, dict) else {}
    by = which.get("by")
    if by and isinstance(by, dict):
        key_spec = by
    else:
        key_spec = _entity_key_spec(e_spec)
    return _compute_entity_id(row, key_spec)


def _iter_dict_rows(csv_path: str, limit: Optional[int] = None, *, delimiter: Optional[str] = None) -> Iterable[Dict[str, Any]]:
    # Use tools to sniff dialect and read rows; then convert to dicts
    dialect = sniff_csv(csv_path, delimiter=delimiter)
    rows = read_rows(csv_path, dialect, limit=limit if limit is not None else 1_000_000_000)
    if not rows:
        return []
    headers = rows[0]
    for r in rows[1:]:
        # Normalize length
        if len(r) < len(headers):
            r = r + [""] * (len(headers) - len(r))
        elif len(r) > len(headers):
            r = r[: len(headers)]
        yield {h: v for h, v in zip(headers, r)}


def transform_csv_to_kg(
    csv_path: str,
    mapping: Dict[str, Any],
    *,
    limit: Optional[int] = None,
    delimiter: Optional[str] = None,
) -> Dict[str, Any]:
    """Convert CSV rows into a minimal KG payload using the mapping.

    Returns {entities: [str], relations: [[s,p,t]]}.
    """
    logger.info("[transform] start path=%s", csv_path)

    entities: Set[str] = set()
    relations: Set[Tuple[str, str, str]] = set()

    ent_map: Dict[str, Any] = mapping.get("entities", {}) if isinstance(mapping.get("entities"), dict) else {}
    edges = mapping.get("edges", []) or []
    null_policy = (mapping.get("options", {}) or {}).get("null_policy", "skip")

    row_count = 0
    for row in _iter_dict_rows(csv_path, limit=limit, delimiter=delimiter):
        row_count += 1
        # Create nodes for each entity spec (if key is resolvable from row)
        for e_name, e_spec in ent_map.items():
            node_id = _compute_entity_id(row, _entity_key_spec(e_spec))
            if node_id:
                entities.add(node_id)

        # Create edges
        for e in edges:
            pred = e.get("predicate") or e.get("label") or e.get("relation")
            if not pred:
                continue
            src = e.get("source") or {}
            tgt = e.get("target") or {}
            src_id = _resolve_node_id(row, mapping, src)
            tgt_id = _resolve_node_id(row, mapping, tgt)
            if not src_id or not tgt_id:
                if null_policy != "keep":
                    continue
            else:
                # Ensure referenced nodes exist
                entities.add(src_id)
                entities.add(tgt_id)
                relations.add((src_id, pred, tgt_id))

    logger.info(
        "[transform] done rows=%d entities=%d relations=%d",
        row_count,
        len(entities),
        len(relations),
    )
    return {
        "entities": sorted(entities),
        "relations": [list(t) for t in sorted(relations)],
    }


def write_kg_json(payload: Dict[str, Any], out_path: str) -> None:
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    logger.info("[transform] wrote KG JSON to %s", out_path)


__all__ = [
    "transform_csv_to_kg",
    "write_kg_json",
]

