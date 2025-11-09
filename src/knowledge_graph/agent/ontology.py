"""Second-stage agent utilities to generate an ontology from a CSV analysis.

Given an LLM-produced analysis of CSV columns (semantics, candidate entities,
relationships, anomalies), this module prompts an LLM to synthesize a
machine-readable ontology (JSON) suitable for mapping.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional


logger = logging.getLogger("knowledgeAgent.agent.ontology")


SCHEMA_DESC = {
    "type": "object",
    "properties": {
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "key": {"type": "string"},
                    "attributes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "type": {"type": "string"},
                                "description": {"type": "string"},
                                "required": {"type": "boolean"},
                            },
                            "required": ["name", "type"],
                        },
                    },
                },
                "required": ["name"],
            },
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "predicate": {"type": "string"},
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "cardinality": {"type": "string"},
                    "description": {"type": "string"},
                    "constraints": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["predicate", "source", "target"],
            },
        },
        "notes": {"type": "string"},
    },
    "required": ["entities", "relationships"],
}


# PROMPT_TEMPLATE = (
#     "You are an ontology engineer. Based on the CSV column analysis below, "
#     "produce a concise JSON ontology with 'entities' and 'relationships'.\n\n"
#     "Requirements:\n"
#     "- For each entity: name, optional description, key (if obvious), and attributes (name, type, description, required).\n"
#     "- For each relationship: predicate, source, target, cardinality (e.g., one_to_many), optional description, optional constraints.\n"
#     "- Only output JSON. No extra text, no markdown fences.\n"
#     "- Keep it minimal but usable.\n\n"
#     "CSV Analysis:\n{analysis}\n"
# )

PROMPT_TEMPLATE = ("""You are an expert ontology engineer. Analyze the CSV column data below and generate a precise JSON ontology.

  ## Output Format (strict JSON, no markdown, no explanatory text):

  {{
  "entities": [
  {{
  "name": "EntityName",
  "description": "Brief description",
  "primary_key": "column_name or null",
  "attributes": [
  {{
  "name": "attribute_name",
  "type": "string|integer|float|boolean|date|datetime|enum",
  "description": "What this represents",
  "required": true|false,
  "constraints": {{"enum_values": [...], "pattern": "...", "min": 0, "max": 100}}
  }}
  ]
  }}
  ],
  "relationships": [
  {{
  "predicate": "descriptive_relationship_name",
  "source": "SourceEntity",
  "target": "TargetEntity",
  "cardinality": "one_to_one|one_to_many|many_to_one|many_to_many",
  "description": "How source relates to target",
  "join_columns": {{"source_col": "...", "target_col": "..."}},
  "required": true|false
  }}
  ]
  }}

  ## Instructions:

  1. Entity Identification: Group related columns into logical entities. Consider:
      - Columns with common prefixes/suffixes that describe the same domain object
      - ID columns that suggest separate entities
      - Repeating patterns indicating entity boundaries
  2. Primary Keys: Identify unique identifiers (ID columns, codes, or natural keys)
  3. Data Types: Infer from column names and sample values:
      - Use 'enum' for categorical with limited distinct values
      - Use 'date'/'datetime' for temporal data
      - Be specific with numeric types (integer vs float)
  4. Relationships: Detect foreign key patterns:
      - Columns ending in '_id', '_code', or matching another entity's primary key
      - Name relationships semantically (e.g., 'belongs_to', 'has_many', 'references')
      - Specify join_columns for traceability
  5. Required Fields: Mark as required if:
      - Column name suggests it (e.g., 'required_', no 'optional_' prefix)
      - It's a primary key or critical business field
      - Analysis shows no nulls/missing values
  6. Constraints: Add when relevant:
      - enum_values for categorical fields
      - min/max for bounded numeric fields
      - pattern for formatted strings (emails, phone numbers)

  ## CSV Column Analysis:

  {analysis}

  ## Output (JSON only, start immediately with '{{'):

  """
  )


def _extract_json(text: str) -> str:
    """Extract a JSON payload from raw LLM text (handles code fences)."""
    # Remove code fences if present
    fence = re.search(r"```json\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fence:
        return fence.group(1)
    fence = re.search(r"```\s*(.*?)\s*```", text, flags=re.DOTALL)
    if fence:
        return fence.group(1)
    return text.strip()


def generate_ontology_from_analysis(analysis_text: str, *, llm_service: Optional[Any] = None) -> Dict[str, Any]:
    """Call an LLM to synthesize an ontology JSON from an analysis string.

    Returns a dict with keys 'entities', 'relationships', and optional 'notes'.
    On parse error, returns {'raw': <llm_text>}.
    """
    from knowledge_graph.llm.service import LLMService
    from langchain_core.prompts import ChatPromptTemplate

    logger.info("[ontology] generate_ontology_from_analysis start chars=%d", len(analysis_text or ""))
    svc = llm_service or LLMService()

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are precise and schema-faithful."),
        ("human", PROMPT_TEMPLATE),
    ])

    chain = prompt | svc.llm
    resp = chain.invoke({"analysis": analysis_text})
    text = getattr(resp, "content", None) or str(resp)
    logger.debug("[ontology] raw response chars=%d", len(text))

    payload = _extract_json(text)
    try:
        obj = json.loads(payload)
        # Basic shape check
        if not isinstance(obj, dict) or "entities" not in obj or "relationships" not in obj:
            logger.warning("[ontology] JSON missing required keys; returning raw")
            return {"raw": text}
        logger.info(
            "[ontology] parsed entities=%d relationships=%d",
            len(obj.get("entities") or []),
            len(obj.get("relationships") or []),
        )
        return obj
    except Exception as exc:
        logger.exception("[ontology] JSON parse failed: %s", exc)
        return {"raw": text}


def format_ontology_pretty(ontology: Dict[str, Any]) -> str:
    """Return a readable string (YAML-like) for quick inspection."""
    try:
        import yaml  # optional
        return yaml.safe_dump(ontology, sort_keys=False)
    except Exception:
        return json.dumps(ontology, indent=2)


__all__ = [
    "generate_ontology_from_analysis",
    "format_ontology_pretty",
]

