"""Minimal mapping-based CSV→KG pipeline (agent-only pilot).

Usage:
  PYTHONPATH=src python -m knowledge_graph.agent.pipeline_map \
    --csv src/knowledge_graph/agent/testdata/people.csv \
    --mapping src/knowledge_graph/agent/mappings/people.mapping.json \
    --out /tmp/people_kg.json
"""

from __future__ import annotations

import argparse
import json
import logging
from typing import Optional

from .transformer import transform_csv_to_kg, write_kg_json


logger = logging.getLogger("knowledgeAgent.agent.pipeline_map")


def run(csv_path: str, mapping_path: str, *, out_path: Optional[str] = None, limit: Optional[int] = None) -> dict:
    with open(mapping_path, "r", encoding="utf-8") as f:
        mapping = json.load(f)
    logger.info("[map] loaded mapping from %s", mapping_path)
    kg = transform_csv_to_kg(csv_path, mapping, limit=limit)
    if out_path:
        write_kg_json(kg, out_path)
    else:
        print(json.dumps(kg, indent=2))
    return kg


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Mapping-based CSV→KG pilot")
    p.add_argument("--csv", required=True, help="Path to CSV file")
    p.add_argument("--mapping", required=True, help="Path to mapping JSON")
    p.add_argument("--out", help="Output KG JSON path")
    p.add_argument("--limit", type=int, default=None, help="Process at most N rows")
    return p.parse_args(argv)


def _main(argv: Optional[list[str]] = None) -> int:
    # Lightweight logging setup for CLI runs if nothing configured
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    args = _parse_args(argv)
    try:
        run(args.csv, args.mapping, out_path=args.out, limit=args.limit)
        return 0
    except Exception as exc:
        logger.exception("[map] failed: %s", exc)
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
