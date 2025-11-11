"""Step to validate an ontology spec against CSV profile."""

from __future__ import annotations

import logging
from typing import List
from ...document_pipeline import DocumentPipelineContext, PipelineStep

logger = logging.getLogger("knowledgeAgent.pipeline.csv.validate_ontology")


class ValidateOntologyStep(PipelineStep):
    name = "validate_ontology"

    def __init__(self, *, min_entities: int = 1, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self.min_entities = min_entities

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return self.enabled and hasattr(context, "ontology_spec") and bool(getattr(context, "ontology_spec", None))

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        ontology = getattr(context, "ontology_spec", None)
        profile = getattr(context, "csv_profile", None)
        issues: List[str] = []
        valid = True

        # Basic structure checks
        try:
            entities = (ontology or {}).get("entities", []) if isinstance(ontology, dict) else []
            relationships = (ontology or {}).get("relationships", []) if isinstance(ontology, dict) else []
            if len(entities) < self.min_entities:
                valid = False
                issues.append(f"requires at least {self.min_entities} entity")

            # Header existence checks (case-insensitive)
            headers = []
            headers_lc = []
            if profile is not None:
                try:
                    headers = getattr(profile, "headers_original", []) or []
                    headers_lc = [str(h).strip().lower() for h in headers]
                except Exception:
                    headers_lc = []

            # Entities: primary_key/key columns should exist if provided
            for e in entities or []:
                pk = e.get("primary_key") or e.get("key")
                if isinstance(pk, str) and pk.strip():
                    if headers_lc and pk.strip().lower() not in headers_lc:
                        valid = False
                        issues.append(f"entity '{e.get('name')}' primary_key '{pk}' not in headers")

            # Relationships: validate join_columns if present
            for r in relationships or []:
                join = r.get("join_columns") or {}
                sc = join.get("source_col") if isinstance(join, dict) else None
                tc = join.get("target_col") if isinstance(join, dict) else None
                if sc and headers_lc and sc.strip().lower() not in headers_lc:
                    valid = False
                    issues.append(f"relationship '{r.get('predicate')}' source_col '{sc}' not in headers")
                if tc and headers_lc and tc.strip().lower() not in headers_lc:
                    valid = False
                    issues.append(f"relationship '{r.get('predicate')}' target_col '{tc}' not in headers")
        except Exception as exc:
            valid = False
            issues.append(f"exception during validation: {exc}")

        context.results[self.name] = {"valid": valid, "issues": issues}
        return context
