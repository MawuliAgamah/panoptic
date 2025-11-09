"""Agent pipeline to analyze a CSV and generate an ontology.

Steps:
 1) Read CSV headers + sample rows (tool)
 2) Analyze columns (LLM or local heuristic)
 3) Generate ontology from the analysis (LLM)

CLI:
  PYTHONPATH=src python -m knowledge_graph.agent.pipeline /path/to.csv --llm --out ontology.json
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from typing import Optional

from knowledge_graph.agent.agent import CsvAnalysisAgent
from knowledge_graph.agent.ontology import (
    generate_ontology_from_analysis,
    format_ontology_pretty,
)


logger = logging.getLogger("knowledgeAgent.agent.pipeline")


def run_pipeline(
    csv_path: str,
    *,
    use_llm_analysis: bool = True,
    sample_rows: int = 30,
    out_path: Optional[str] = None,
    print_pretty: bool = True,
) -> dict:
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"File not found: {csv_path}")

    logger.info(
        "[pipeline] start path=%s use_llm_analysis=%s sample_rows=%d",
        csv_path,
        use_llm_analysis,
        sample_rows,
    )

    agent = CsvAnalysisAgent()

    # Step 1: analysis
    if use_llm_analysis:
        analysis_text = agent.analyze_with_llm(csv_path, sample_rows=sample_rows)
    else:
        analysis_obj = agent.analyze_csv_columns(csv_path, sample_rows=1000)
        analysis_text = agent.format_analysis(analysis_obj)

    # Step 2: ontology synthesis
    ontology = generate_ontology_from_analysis(analysis_text)

    # Emit
    if out_path:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(ontology, f, indent=2)
        logger.info("[pipeline] wrote ontology to %s", out_path)

    if print_pretty:
        print(format_ontology_pretty(ontology))

    logger.info(
        "[pipeline] done entities=%s relationships=%s",
        len(ontology.get("entities", []) if isinstance(ontology, dict) else []),
        len(ontology.get("relationships", []) if isinstance(ontology, dict) else []),
    )
    return ontology


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="CSV→Ontology agent pipeline")
    p.add_argument("csv", help="Path to CSV file")
    p.add_argument("--no-llm", dest="llm", action="store_false", help="Use local analysis instead of LLM for step 1")
    p.add_argument("--llm", dest="llm", action="store_true", help="Force LLM analysis for step 1 (default)")
    p.set_defaults(llm=True)
    p.add_argument("--sample-rows", type=int, default=30, help="Rows to include in the LLM analysis prompt")
    p.add_argument("--out", type=str, default=None, help="Write ontology JSON to this file")
    p.add_argument("--no-print", dest="print_pretty", action="store_false", help="Do not pretty-print ontology to stdout")
    p.set_defaults(print_pretty=True)
    return p.parse_args(argv)


def _main(argv: Optional[list[str]] = None) -> int:
    args = _parse_args(argv)
    try:
        run_pipeline(
            args.csv,
            use_llm_analysis=args.llm,
            sample_rows=args.sample_rows,
            out_path=args.out,
            print_pretty=args.print_pretty,
        )
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        logger.exception("[pipeline] failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())

