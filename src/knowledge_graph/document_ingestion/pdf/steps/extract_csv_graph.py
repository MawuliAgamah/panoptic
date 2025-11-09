"""Step to build a knowledge graph directly from CSV files.

Supported CSV shapes (header names are case-insensitive):
- Edge list: columns for source, target, optional predicate/relation.
- Node table: a column 'name' or 'label' creates nodes; optional 'type' accepted.

The step persists the resulting KG to the DB and attaches it to document.knowledge_graph.
"""

from __future__ import annotations

import logging
import csv
from typing import Any, Dict, List, Tuple

from ...document_pipeline import DocumentPipelineContext, PipelineStep


logger = logging.getLogger("knowledgeAgent.pipeline.csv")


SOURCE_ALIASES = {"source", "src", "from", "subject", "head", "left"}
TARGET_ALIASES = {"target", "dst", "to", "object", "tail", "right"}
PRED_ALIASES = {"predicate", "relation", "rel", "edge", "label", "type"}
NAME_ALIASES = {"name", "label", "id", "title"}
TYPE_ALIASES = {"type", "category", "class"}


def _match(col: str, aliases: set[str]) -> bool:
    return col.strip().lower() in aliases


def _read_csv_rows(path: str) -> Tuple[List[str], List[List[str]]]:
    with open(path, "r", encoding="utf-8", newline="") as f:
        sample = f.read(2048)
        f.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample)
        except Exception:
            dialect = csv.excel
        reader = csv.reader(f, dialect)
        rows = list(reader)
        if not rows:
            return [], []
        headers = [h.strip() for h in rows[0]]
        return headers, rows[1:]


class ExtractCsvGraphStep(PipelineStep):
    name = "extract_csv_graph"

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def should_run(self, context: DocumentPipelineContext) -> bool:
        if not self.enabled:
            return False
        doc = context.document
        if not doc:
            return False
        ft = (getattr(doc, "file_type", "") or "").lower()
        return ft in {".csv", "csv"}

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        document = context.ensure_document()
        db = context.services.db_client
        if not db:
            logger.warning("DB client unavailable; CSV graph will not be persisted")

        headers, rows = _read_csv_rows(document.file_path)
        if not headers:
            context.results[self.name] = {"rows": 0, "entities": 0, "relations": 0, "error": "no_headers"}
            return context

        # Detect schema
        idx_source = idx_target = idx_pred = None
        idx_name = idx_type = None
        for i, h in enumerate(headers):
            if idx_source is None and _match(h, SOURCE_ALIASES):
                idx_source = i
            if idx_target is None and _match(h, TARGET_ALIASES):
                idx_target = i
            if idx_pred is None and _match(h, PRED_ALIASES):
                idx_pred = i
            if idx_name is None and _match(h, NAME_ALIASES):
                idx_name = i
            if idx_type is None and _match(h, TYPE_ALIASES):
                idx_type = i

        entities: set[str] = set()
        relations: List[List[str]] = []

        if idx_source is not None and idx_target is not None:  # Edge list
            for r in rows:
                try:
                    s = (r[idx_source] if idx_source < len(r) else "").strip()
                    t = (r[idx_target] if idx_target < len(r) else "").strip()
                    if not s or not t:
                        continue
                    p = (r[idx_pred] if (idx_pred is not None and idx_pred < len(r)) else "related_to").strip() or "related_to"
                    entities.add(s)
                    entities.add(t)
                    relations.append([s, p, t])
                except Exception:
                    continue
            schema = "edge_list"
        elif idx_name is not None:  # Node table
            for r in rows:
                name = (r[idx_name] if idx_name < len(r) else "").strip()
                if name:
                    entities.add(name)
            schema = "node_table"
        else:
            # Fallback: use first column as node names
            if headers:
                for r in rows:
                    v = (r[0] if r else "").strip()
                    if v:
                        entities.add(v)
            schema = "fallback_nodes"

        kg = {"entities": list(entities), "relations": relations}
        document.knowledge_graph = kg
        document.is_kg_extracted = True

        # Persist KG (idempotent upsert in SQLite layer)
        persisted = False
        if db:
            try:
                persisted = db.save_knowledge_graph(document.id, kg)
            except Exception as exc:
                logger.exception("Failed to persist CSV KG for %s: %s", document.id, exc)

        logger.info(
            "%s: CSV graph parsed schema=%s entities=%d relations=%d persisted=%s",
            document.id,
            schema,
            len(entities),
            len(relations),
            persisted,
        )

        context.set_document(document)
        context.results[self.name] = {
            "schema": schema,
            "rows": len(rows),
            "entities": len(entities),
            "relations": len(relations),
            "persisted": bool(persisted),
        }
        return context
