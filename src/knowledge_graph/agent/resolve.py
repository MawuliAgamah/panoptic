"""CLI to resolve duplicate nodes in a KG JSON file.

Usage:
  PYTHONPATH=src python -m knowledge_graph.agent.resolve /path/to/kg.json

Options:
  --out /path/to/out.json         Output path (defaults to <kg>_resolved.json)
  --protect txn,date,custom       Comma-separated prefixes to protect from merging
  --synonyms /path/to/syn.json    JSON file mapping per-prefix synonyms, shape:
                                  { "product": { "amarilla": "Amarilla" } }
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .entity_resolution import resolve_entities, resolve_entities_simple


logger = logging.getLogger("knowledgeAgent.agent.resolve")


def run(in_path: str, *, out_path: Optional[str] = None, protect: Optional[str] = None, synonyms_path: Optional[str] = None, simple: bool = False, prune_isolates: bool = False) -> Dict[str, Any]:
    in_p = Path(in_path)
    if not in_p.exists():
        raise FileNotFoundError(f"Input not found: {in_p}")

    if out_path is None:
        out_p = in_p.with_name(in_p.stem + "_resolved.json")
    else:
        out_p = Path(out_path)

    prot = None
    if protect:
        prot = [p.strip() for p in protect.split(',') if p.strip()]

    syn = None
    if synonyms_path:
        sp = Path(synonyms_path)
        if not sp.exists():
            raise FileNotFoundError(f"Synonyms file not found: {sp}")
        with sp.open('r', encoding='utf-8') as f:
            syn = json.load(f)

    with in_p.open('r', encoding='utf-8') as f:
        kg = json.load(f)

    logger.info("[resolve] input: %s", in_p)
    if simple:
        resolved, stats = resolve_entities_simple(kg, ignore_prefix=True, prune_isolates=prune_isolates)
    else:
        resolved, stats = resolve_entities(kg, protected_prefixes=prot, synonyms=syn)
    with out_p.open('w', encoding='utf-8') as f:
        json.dump(resolved, f, indent=2)
    logger.info("[resolve] wrote: %s", out_p)
    logger.info("[resolve] stats: %s", stats)
    return resolved


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Resolve duplicate nodes in a KG JSON file")
    p.add_argument("kg", help="Path to KG JSON file {entities:[], relations:[]}")
    p.add_argument("--out", default=None, help="Output KG JSON path (default: <kg>_resolved.json)")
    p.add_argument("--protect", default=None, help="Comma-separated protected prefixes (e.g., 'txn,date')")
    p.add_argument("--synonyms", default=None, help="JSON file with per-prefix synonyms")
    p.add_argument("--simple", action="store_true", help="Use simple label-based merge (ignores prefixes, drops punctuation)")
    p.add_argument("--prune-isolates", action="store_true", help="Remove nodes with degree 0 after resolving")
    return p.parse_args(argv)


def _main(argv: Optional[list[str]] = None) -> int:
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')
    args = _parse_args(argv)
    try:
        run(args.kg, out_path=args.out, protect=args.protect, synonyms_path=args.synonyms, simple=args.simple, prune_isolates=args.prune_isolates)
        return 0
    except Exception as exc:
        logger.exception("[resolve] failed: %s", exc)
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
