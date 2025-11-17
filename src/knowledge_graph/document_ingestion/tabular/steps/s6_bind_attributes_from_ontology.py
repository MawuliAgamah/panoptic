"""Bind attributes from ontology to CSV columns using csv_profile headers.

Adds attribute mappings to context.mapping_spec.entities[entity]['attributes'].
Heuristics:
 - case-insensitive exact match to header
 - snake-case match to header
 - contains match (normalized)
Logs a concise summary so you can verify bindings.
"""

from __future__ import annotations

import logging
from typing import Dict, Any, List
import json
from ...document_pipeline import DocumentPipelineContext, PipelineStep
from knowledge_graph.logging_utils import green
logger = logging.getLogger("knowledgeAgent.pipeline.csv.bind_attributes")


def _to_snake(name: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9]+", "_", (name or "").strip()).strip("_").lower()


class BindAttributesFromOntologyStep(PipelineStep):
    name = "bind_attributes_from_ontology"

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return (
            self.enabled
            and bool(getattr(context, "ontology_specification", None))
            and bool(getattr(context, "mapping_spec", None))
            and bool(getattr(context, "csv_profile", None))
        )

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        logger.info(green("--------------------------------- Step 5: Bind Attributes From Ontology---------------------------------"))
        
        ontology: Dict[str, Any] = getattr(context, "ontology_specification", {}) or {}
        mapping: Dict[str, Any] = getattr(context, "mapping_spec", {}) or {}
        profile = getattr(context, "csv_profile", None)

        headers: List[str] = getattr(profile, "headers_original", []) or []
        headers_lc: List[str] = [str(h).strip().lower() for h in headers]
        norm_to_orig: Dict[str, str] = {h.lower(): h for h in headers}

        ents = ontology.get("entities", []) if isinstance(ontology, dict) else []
        mapping_entities: Dict[str, Any] = mapping.get("entities", {}) if isinstance(mapping.get("entities"), dict) else {}

        bound = 0
        warnings: List[str] = []

        for e in ents:
            name = str(e.get("name") or "Entity").strip() or "Entity"
            attrs = e.get("attributes") or []
            if name not in mapping_entities:
                # Ensure entity exists in mapping
                mapping_entities[name] = {"key": {}, "attributes": []}
            if not isinstance(mapping_entities[name].get("attributes"), list):
                mapping_entities[name]["attributes"] = []

            existing = {a.get("name") for a in (mapping_entities[name]["attributes"] or []) if isinstance(a, dict)}

            for a in attrs:
                attr_name = str(a.get("name") or "").strip()
                if not attr_name or attr_name in existing:
                    continue
                attr_snake = _to_snake(attr_name)

                chosen: str | None = None
                # 1) exact case-insensitive match
                if attr_name.lower() in headers_lc:
                    chosen = norm_to_orig[attr_name.lower()]
                # 2) snake-case match
                elif attr_snake in headers_lc:
                    chosen = norm_to_orig[attr_snake]
                else:
                    # 3) contains match (normalized)
                    for h in headers_lc:
                        if attr_snake and attr_snake in h.replace("_", ""):
                            chosen = norm_to_orig[h]
                            break

                if chosen:
                    mapping_entities[name]["attributes"].append({"name": attr_name, "column": chosen})
                    bound += 1
                else:
                    warnings.append(f"entity '{name}': attribute '{attr_name}' not matched to any header")

        # write back entities
        mapping["entities"] = mapping_entities
        setattr(context, "mapping_spec", mapping)

        # Pretty-print mapping for observability
        try:
            logger.info("%s: mapping (with attributes): %s",
                        getattr(context.document, 'id', '-'), json.dumps(mapping, indent=2))
        except Exception:
            pass

        logger.info("%s: attributes bound=%d (entities=%d) warnings=%d",
                    getattr(context.document, 'id', '-'), bound, len(mapping_entities), len(warnings))
        context.results[self.name] = {"bound": bound, "warnings": warnings}
        return context
