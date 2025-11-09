"""End-to-end agent pipeline from CSV only:

1) LLM column analysis
2) LLM ontology synthesis
3) Compile mapping from ontology + CSV headers
4) Transform CSV → KG JSON

Usage:
  PYTHONPATH=src python -m knowledge_graph.agent.pipeline_auto \
    --csv /path/to.csv \
    --out /tmp/kg.json \
    --save-mapping /tmp/mapping.json \
    --sample-rows 30
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Optional

from .agent import CsvAnalysisAgent
from .ontology import generate_ontology_from_analysis
from .mapping import compile_mapping_from_ontology
from .tools import sniff_csv, read_rows
from .transformer import transform_csv_to_kg, write_kg_json
from .entity_resolution import resolve_entities


logger = logging.getLogger("knowledgeAgent.agent.pipeline_auto")


def _csv_headers(path: str, sample_rows: int = 1, *, delimiter: Optional[str] = None) -> list[str]:
    d = sniff_csv(path, delimiter=delimiter)
    rows = read_rows(path, d, limit=sample_rows)
    if not rows:
        return []
    return rows[0]


def run(csv_path: str, *, sample_rows: int = 30, out_path: Optional[str] = None, save_mapping: Optional[str] = None, delimiter: Optional[str] = None, er: bool = True) -> dict:
    logger.info("[auto] start csv=%s sample_rows=%d", csv_path, sample_rows)

    # 1) Column analysis (LLM)
    agent = CsvAnalysisAgent()
    analysis_text = agent.analyze_with_llm(csv_path, sample_rows=sample_rows, delimiter=delimiter)
    try:
        logger.info("[auto] analysis text (first 2000 chars):\n%s", (analysis_text or "")[:2000])
    except Exception:
        pass

    # 2) Ontology
    ontology = generate_ontology_from_analysis(analysis_text)
    try:
        logger.info("[auto] ontology JSON:\n%s", json.dumps(ontology, indent=2))
    except Exception:
        pass

    # 3) Compile mapping
    headers = _csv_headers(csv_path, delimiter=delimiter)
    try:
        logger.info("[auto] detected headers: %s", headers)
    except Exception:
        pass
    mapping, warnings = compile_mapping_from_ontology(ontology, headers)
    for w in warnings:
        logger.warning("[auto] mapping warning: %s", w)
    if save_mapping:
        with open(save_mapping, "w", encoding="utf-8") as f:
            json.dump(mapping, f, indent=2)
        logger.info("[auto] mapping saved to %s", save_mapping)
    try:
        logger.info("[auto] compiled mapping:\n%s", json.dumps(mapping, indent=2))
    except Exception:
        pass

    # 4) Transform
    # Defaults: write outputs next to the CSV if not provided
    if out_path is None or save_mapping is None:
        try:
            from pathlib import Path
            base = Path(csv_path)
            if out_path is None:
                out_path = str(base.parent / f"{base.stem}_kg.json")
            if save_mapping is None:
                save_mapping = str(base.parent / f"{base.stem}_mapping.json")
        except Exception:
            # Fallback to tmp
            if out_path is None:
                out_path = "/tmp/kg.json"
            if save_mapping is None:
                save_mapping = "/tmp/mapping.json"

    kg = transform_csv_to_kg(csv_path, mapping, delimiter=delimiter)
    if er:
        kg_resolved, er_stats = resolve_entities(kg)
        try:
            logger.info("[auto] ER stats: %s", er_stats)
        except Exception:
            pass
        kg = kg_resolved
    try:
        # Log small samples so logs stay readable
        entities = kg.get("entities", []) or []
        relations = kg.get("relations", []) or []
        logger.info("[auto] kg sample entities (up to 10): %s", entities[:10])
        logger.info("[auto] kg sample relations (up to 10): %s", relations[:10])
    except Exception:
        pass
    write_kg_json(kg, out_path)
    logger.info("[auto] done entities=%d relations=%d", len(kg.get("entities", [])), len(kg.get("relations", [])))
    return kg


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CSV-only end-to-end agent pipeline")
    # Simplified: only positional CSV is required; others optional
    p.add_argument("csv", help="Path to CSV file")
    p.add_argument("--out", default=None, help="Output KG JSON path (defaults to <csv>_kg.json)")
    p.add_argument("--save-mapping", default=None, help="Save compiled mapping (defaults to <csv>_mapping.json)")
    p.add_argument("--sample-rows", type=int, default=30, help="Rows to include in LLM analysis prompt")
    p.add_argument("--delimiter", default=None, help="Force CSV delimiter (e.g., ',' or '\t')")
    p.add_argument("--no-er", dest="er", action="store_false", help="Disable entity resolution merge step")
    p.set_defaults(er=True)
    return p.parse_args(argv)


def _main(argv: Optional[list[str]] = None) -> int:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    args = _parse_args(argv)
    try:
        run(args.csv, sample_rows=args.sample_rows, out_path=args.out, save_mapping=args.save_mapping, delimiter=args.delimiter, er=args.er)
        return 0
    except Exception as exc:
        logger.exception("[auto] failed: %s", exc)
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
