"""Populate missing primary keys in the mapping by synthesizing reasonable defaults.

Strategy:
 - If ontology declares a key present in headers, keep it (already set by compile step).
 - For missing keys:
    * Prefer a header that looks like '<entity>_id' (snake-case), if present
    * Else, reuse a join column from edges referencing this entity (target/source), if present
    * Else, fallback to the first header (noisy) and log a warning

This ensures downstream transforms can build node identifiers deterministically.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List
from ...document_pipeline import DocumentPipelineContext, PipelineStep

logger = logging.getLogger("knowledgeAgent.pipeline.csv.populate_keys")


def _to_snake(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip()).strip("_").lower()


class PopulateMissingPrimaryKeysStep(PipelineStep):
    name = "populate_missing_primary_keys"

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return self.enabled and bool(getattr(context, "mapping_spec", None)) and bool(getattr(context, "csv_profile", None))

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        mapping: Dict[str, Any] = getattr(context, "mapping_spec", {}) or {}
        profile = getattr(context, "csv_profile", None)
        headers: List[str] = getattr(profile, "headers_original", []) or []
        headers_lc: List[str] = [str(h).strip().lower() for h in headers]
        norm_to_orig: Dict[str, str] = {h.lower(): h for h in headers}

        ents: Dict[str, Any] = mapping.get("entities", {}) if isinstance(mapping.get("entities"), dict) else {}
        edges: List[Dict[str, Any]] = mapping.get("edges", []) or []

        filled = 0
        warnings: List[str] = []

        for entity_name, spec in ents.items():
            key_spec = (spec or {}).get("key") or {}
            has_key = bool((key_spec.get("column") or key_spec.get("template")))
            if has_key:
                continue

            # 1) Prefer <entity>_id style header
            snake = _to_snake(entity_name)
            candidate = f"{snake}_id" if snake else None
            chosen: str | None = None
            if candidate and candidate in headers_lc:
                chosen = norm_to_orig[candidate]

            # 2) Reuse join column from edges that reference this entity
            if not chosen:
                for e in edges:
                    # target side
                    try:
                        tgt = str(((e.get("target") or {}).get("entity")) or "")
                        if tgt == entity_name:
                            c = ((e.get("target") or {}).get("by") or {}).get("column")
                            if c and c.strip() and c.strip().lower() in headers_lc:
                                chosen = norm_to_orig[c.strip().lower()]
                                break
                    except Exception:
                        pass
                    # source side
                    try:
                        src = str(((e.get("source") or {}).get("entity")) or "")
                        if src == entity_name:
                            c = ((e.get("source") or {}).get("by") or {}).get("column")
                            if c and c.strip() and c.strip().lower() in headers_lc:
                                chosen = norm_to_orig[c.strip().lower()]
                                break
                    except Exception:
                        pass

            # 3) Fallback: first header, warn
            if not chosen and headers:
                chosen = headers[0]
                warnings.append(f"entity '{entity_name}': synthesized key using first header '{chosen}' (fallback)")

            if chosen:
                spec["key"] = {"column": chosen}
                ents[entity_name] = spec
                filled += 1
            else:
                warnings.append(f"entity '{entity_name}': could not synthesize a key (no headers)")

        mapping["entities"] = ents
        setattr(context, "mapping_spec", mapping)
        logger.info("%s: synthesized keys for %d entities (entities=%d) warnings=%d",
                    getattr(context.document, 'id', '-'), filled, len(ents), len(warnings))
        context.results[self.name] = {"filled": filled, "warnings": warnings}
        return context

