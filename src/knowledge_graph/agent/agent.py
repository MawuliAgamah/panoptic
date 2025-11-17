"""Lightweight CSV analysis agent.

Goal: given a CSV path, read columns and return a concise analysis
without any external model calls. This is the simplest usable
implementation: it "uses a tool" (file read) and infers basic types.

Usage (programmatic):
    from knowledge_graph.agent.agent import CsvAnalysisAgent
    agent = CsvAnalysisAgent()
    result = agent.analyze_csv_columns("/path/to/file.csv")
    print(agent.format_analysis(result))

CLI (optional):
    python -m knowledge_graph.agent.agent /path/to/file.csv
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import os
import re
import random
import logging
import time


logger = logging.getLogger("knowledgeAgent.agent.csv")


# --- Prompt

PROMPT_TEMPLATE = """

You are a data modeling expert specializing in knowledge graph design. 


Analyze the CSV structure below to inform knowledge graph ontology design.

## Dataset Information:
File: {os.path.abspath(path)}
Delimiter: {delim}
Columns: {', '.join(headers)}

## Sample Data:
```markdown
{sample_md}
```

## Required Analysis:
### 1. ENTITY IDENTIFICATION
For each potential entity:
                - Entity name and description
- Which columns belong to this entity
- Suggested primary key (single column or composite)
- Justification for entity boundary

### 2. COLUMN CLASSIFICATION
For each column, identify:
- **Entity assignment**: Which entity does it belong to?
- **Role**: Intrinsic attribute | Foreign key | Derived/calculated | Temporal context
- **Data type**: string | integer | float | boolean | date | datetime | enum
- **Cardinality**: Unique values (high/medium/low) if observable from sample
- **Nullability**: Required or optional (if determinable)

### 3. RELATIONSHIP DETECTION
For each relationship:
    - Source entity -> Target entity
    - Relationship name (use semantic verbs: belongs_to, contains, references, etc.)
- Cardinality: one-to-one | one-to-many | many-to-one | many-to-many
- Join columns: Specify exact source and target column names
- Is this an identifying relationship (part of source entity's key)?
### 4. DATA PATTERNS & ANOMALIES
Note:
- Redundant/denormalized data (same info in multiple columns)
- Hierarchical relationships (parent-child in column names)
- Missing unique identifiers for potential entities  
- Suspicious patterns (mixed types, inconsistent naming, null-heavy columns)
- Columns that might represent many-to-many relationships
- Temporal or versioning patterns (season, date, version fields)

### 5. NORMALIZATION OPPORTUNITIES
Identify:
- Lookup table candidates (repeated categorical values)  
- Composite entities (junction tables for many-to-many)
- Attributes that should be separate entities

## Output Format
Provide analysis in clear sections as outlined above. Be specific with column names and relationships.
Limit total response to 400 words while maintaining completeness.
"""

# --- Data structures ---

@dataclass
class ColumnSummary:
    name: str
    inferred_type: str
    non_null: int
    nulls: int
    distinct: int
    examples: List[str]


@dataclass
class CsvAnalysis:
    path: str
    delimiter: str
    encoding: str
    row_count_sampled: int
    column_count: int
    columns: List[ColumnSummary]


"""Note: the agent uses the shared tabular tools for CSV IO."""
from knowledge_graph.document_ingestion.tabular.agents_tools import sniff_csv, read_rows


# # --- Type inference ---

# _DATE_PATTERNS = [
#     re.compile(r"^\d{4}-\d{2}-\d{2}$"),           # 2024-05-14
#     re.compile(r"^\d{2}/\d{2}/\d{4}$"),           # 05/14/2024
#     re.compile(r"^\d{4}/\d{2}/\d{2}$"),           # 2024/05/14
#     re.compile(r"^\d{2}-\d{2}-\d{4}$"),           # 14-05-2024
# ]


# def _looks_int(s: str) -> bool:
#     try:
#         int(s)
#         return True
#     except Exception:
#         return False


# def _looks_float(s: str) -> bool:
#     try:
#         float(s)
#         # Reject representations like 'NaN'/'inf' as numeric here
#         return not (s.lower() in ("nan", "inf", "+inf", "-inf"))
#     except Exception:
#         return False


# def _looks_bool(s: str) -> bool:
#     return s.strip().lower() in {"true", "false", "t", "f", "yes", "no", "0", "1"}


# def _looks_date(s: str) -> bool:
#     s = s.strip()
#     if not s:
#         return False
#     for rx in _DATE_PATTERNS:
#         if rx.match(s):
#             return True
#     return False


# def _infer_type(values: List[str]) -> str:
#     """Infer a simple type given a sample of string values (non-nulls)."""
#     if not values:
#         return "string"
#     checks = {
#         "integer": all(_looks_int(v) for v in values),
#         "float": all(_looks_float(v) for v in values),
#         "bool": all(_looks_bool(v) for v in values),
#         "date": all(_looks_date(v) for v in values),
#     }
#     for t in ("integer", "float", "bool", "date"):
#         if checks[t]:
#             return t
#     # Mixed numeric? prefer float
#     if all(_looks_int(v) or _looks_float(v) for v in values):
#         return "float"
#     return "string"


# --- Agent ---

class CsvAnalysisAgent:
    """Minimal CSV analysis agent that inspects column names and basic stats.
    It uses internal helper functions as "tools" to read and parse the file safely.
    """

    def analyze_csv_columns(self, path: str, sample_rows: int = 1000) -> CsvAnalysis:
        if not os.path.exists(path):
            raise FileNotFoundError(f"File not found: {path}")

        logger.info("[agent] analyze_csv_columns start path=%s sample_rows=%d", path, sample_rows)
        t0 = time.time()

        dialect = sniff_csv(path)
        rows = read_rows(path, dialect, limit=sample_rows)
        if not rows:
            raise ValueError("CSV appears empty")

        headers = rows[0]
        data = rows[1:]
        col_count = len(headers)
        col_values: List[List[str]] = [[] for _ in range(col_count)]
        null_counts = [0] * col_count
        examples: List[List[str]] = [[] for _ in range(col_count)]

        for r in data:
            # Normalize row length
            if len(r) < col_count:
                r = r + [""] * (col_count - len(r))
            elif len(r) > col_count:
                r = r[:col_count]
            for i, v in enumerate(r):
                val = (v or "").strip()
                if val == "":
                    null_counts[i] += 1
                else:
                    col_values[i].append(val)
                    if len(examples[i]) < 3 and val not in examples[i]:
                        examples[i].append(val)

        summaries: List[ColumnSummary] = []
        for i, name in enumerate(headers):
            non_null = len(col_values[i])
            distinct = len(set(col_values[i]))
            inferred = _infer_type(col_values[i][:200])  # cap for speed
            summaries.append(
                ColumnSummary(
                    name=name,
                    inferred_type=inferred,
                    non_null=non_null,
                    nulls=null_counts[i],
                    distinct=distinct,
                    examples=examples[i],
                )
            )

        analysis = CsvAnalysis(
            path=os.path.abspath(path),
            delimiter=getattr(dialect, "delimiter", ","),
            encoding="utf-8",
            row_count_sampled=len(data),
            column_count=col_count,
            columns=summaries,
        )

        # Debug: per-column quick stats
        for c in summaries:
            try:
                total = c.non_null + c.nulls
                null_pct = (c.nulls / total * 100.0) if total else 0.0
                logger.debug("[agent] col '%s' type=%s distinct=%d nulls=%d(%.1f%%)", c.name, c.inferred_type, c.distinct, c.nulls, null_pct)
            except Exception:
                pass

        logger.info("[agent] analyze_csv_columns done file=%s cols=%d rows(sampled)=%d elapsed_ms=%d",
                    os.path.basename(path), col_count, len(data), int((time.time() - t0) * 1000))
        return analysis

    @staticmethod
    def format_analysis(analysis: CsvAnalysis) -> str:
        lines = [
            f"File: {analysis.path}",
            f"Delimiter: {analysis.delimiter}",
            f"Encoding: {analysis.encoding}",
            f"Columns: {analysis.column_count}",
            f"Rows (sampled): {analysis.row_count_sampled}",
            "",
            "Column summaries:",
        ]
        for c in analysis.columns:
            total = c.non_null + c.nulls
            null_pct = (c.nulls / total * 100.0) if total else 0.0
            ex = ", ".join(c.examples) if c.examples else "—"
            lines.append(
                f"- {c.name}: type={c.inferred_type} distinct={c.distinct} nulls={c.nulls} ({null_pct:.1f}%) examples=[{ex}]"
            )
        return "\n".join(lines)

    # --- LLM-backed analysis ---
    def analyze_with_llm(
        self,
        path: str,
        *,
        sample_rows: int = 30,
        llm_service: Optional[Any] = None,
        delimiter: Optional[str] = None,
    ) -> str:
        """Summarize columns via LLM using a compact sample.

        Requires an LLMService instance (or will construct a default one).
        Returns a concise natural-language analysis.
        """
        # Local read (the "tool")
        logger.info("[agent] analyze_with_llm start path=%s sample_rows=%d", path, sample_rows)
        t0 = time.time()
        dialect = sniff_csv(path, delimiter=delimiter)
        rows = read_rows(path, dialect, limit=sample_rows + 1)
        if not rows:
            raise ValueError("CSV appears empty")
        headers = rows[0]
        data = rows[1:]

        # Build a compact sample (avoid huge prompts); use random sampling of data rows
        sample_rows_count = min(sample_rows, len(data))
        selected_rows = random.sample(data, sample_rows_count) if sample_rows_count > 0 else []
        preview_lines = [headers] + selected_rows
        # Render as Markdown table for improved LLM readability
        delim = getattr(dialect, "delimiter", ",") or ","

        def _to_markdown_table(hdrs, rows_, *, max_cols=None, cell_max_len=120):
            """Convert a csv to a markdown table."""
            try:
                cols = min(len(hdrs), max_cols) if max_cols else len(hdrs)
                def _san(x):
                    s = "" if x is None else str(x)
                    s = s.replace("|", "\\|").replace("\n", " ")
                    return s if len(s) <= cell_max_len else s[: cell_max_len - 1] + "…"
                hdr_row = "| " + " | ".join(_san(h) for h in hdrs[:cols]) + " |"
                sep_row = "| " + " | ".join(["---"] * cols) + " |"
                body_rows = []
                for r in rows_:
                    # normalize row length
                    rr = list(r)[:cols] + [""] * max(0, cols - len(r))
                    body_rows.append("| " + " | ".join(_san(v) for v in rr) + " |")
                return "\n".join([hdr_row, sep_row] + body_rows)
            except Exception:
                # Fallback to simple CSV-like rendering
                return "\n".join(delim.join(map(str, r[: len(hdrs)])) for r in ([hdrs] + list(rows_)))

        sample_md = _to_markdown_table(headers, selected_rows)
        logger.info(
            "[agent] prompt sample built columns=%d rows_in_prompt=%d prompt_chars=%d",
            len(headers),
            len(selected_rows),
            len(sample_md),
        )

        # Write prompt, headers, and a CSV sample to a unified file first
        debug_out_path = None
        try:
            logs_dir = "/Users/mawuliagamah/gitprojects/pre_release/kg_extract/logs"
            os.makedirs(logs_dir, exist_ok=True)
            _ts = int(time.time())
            debug_out_path = os.path.join(logs_dir, f"analysis_text_{_ts}.txt")
            # Build sample text from randomly selected rows (header already separate)
            sample_text = "\n".join(delim.join(map(str, r[: len(headers)])) for r in selected_rows)
            # Compose the full prompt text using a raw template
            prompt_text = f"""
You are a data modeling expert specializing in knowledge graph design.

Analyze the CSV structure below to inform knowledge graph ontology design.

## Dataset Information:
File: {os.path.abspath(path)}
Delimiter: {delim}
Columns: {', '.join(headers)}

## Sample Data:
```markdown
{sample_md}
```

## Required Analysis:
### 1. ENTITY IDENTIFICATION
For each potential entity:
- Entity name and description
- Which columns belong to this entity
- Suggested primary key (single column or composite)
- Justification for entity boundary

### 2. COLUMN CLASSIFICATION
For each column, identify:
- **Entity assignment**: Which entity does it belong to?
- **Role**: Intrinsic attribute | Foreign key | Derived/calculated | Temporal context
- **Data type**: string | integer | float | boolean | date | datetime | enum
- **Cardinality**: Unique values (high/medium/low) if observable from sample
- **Nullability**: Required or optional (if determinable)

### 3. RELATIONSHIP DETECTION
For each relationship:
- Source entity -> Target entity
- Relationship name (use semantic verbs: belongs_to, contains, references, etc.)
- Cardinality: one-to-one | one-to-many | many-to-one | many-to-many
- Join columns: Specify exact source and target column names
- Is this an identifying relationship (part of source entity's key)?

### 4. DATA PATTERNS & ANOMALIES
Note:
- Redundant/denormalized data (same info in multiple columns)
- Hierarchical relationships (parent-child in column names)
- Missing unique identifiers for potential entities
- Suspicious patterns (mixed types, inconsistent naming, null-heavy columns)
- Columns that might represent many-to-many relationships
- Temporal or versioning patterns (season, date, version fields)

### 5. NORMALIZATION OPPORTUNITIES
Identify:
- Lookup table candidates (repeated categorical values)
- Composite entities (junction tables for many-to-many)
- Attributes that should be separate entities

## Output Format
Provide analysis in clear sections as outlined above. Be specific with column names and relationships.
Limit total response to 400 words while maintaining completeness.
"""
            with open(debug_out_path, "w", encoding="utf-8") as f:
                f.write("=== Prompt ===\n")
                f.write(prompt_text + "\n\n")
                f.write("=== Headers ===\n")
                f.write(delim.join(map(str, headers)) + "\n\n")
                # f.write(f"=== Sample (first {sample_rows_count} rows) ===\n")
                # if sample_text:
                #     f.write(sample_text + "\n")
            logger.info("[agent] prompt, headers, and sample written to %s", debug_out_path)
            # Expose the path so downstream ontology generation can append to the same file
            try:
                os.environ["KG_LAST_ANALYSIS_LOG"] = debug_out_path
            except Exception:
                pass
        except Exception:
            logger.warning("[agent] failed to write headers/sample to logs directory", exc_info=True)



        # Lazy import to avoid hard dependency at import time
        from knowledge_graph.llm.service import LLMService
        from langchain_core.prompts import ChatPromptTemplate

        svc = llm_service or LLMService()

        # Build a prompt with the fully-rendered human content
        prompt = ChatPromptTemplate.from_messages([
            ("human", prompt_text)
        ])

        chain = prompt | svc.llm
        response = chain.invoke({})
        # LangChain ChatOpenAI returns a AIMessage with .content
        text = getattr(response, "content", None) or str(response)
        # Append the agent analysis to the same file
        try:
            if debug_out_path:
                with open(debug_out_path, "a", encoding="utf-8") as f:
                    f.write("\n=== Agent Analysis ===\n")
                    f.write(text or "")
                logger.info("[agent] analysis details written to %s", debug_out_path)
        except Exception:
            logger.warning("[agent] failed to append analysis text to logs directory", exc_info=True)
        logger.info("[agent] analyze_with_llm done chars=%d elapsed_ms=%d", len(text or ""), int((time.time() - t0) * 1000))
        return text


def _main(argv: Optional[List[str]] = None) -> int:
    import sys
    args = argv or sys.argv[1:]
    if not args:
        print("Usage: python -m knowledge_graph.agent.agent <path/to.csv> [--llm]")
        return 2
    path = args[0]
    use_llm = "--llm" in args[1:]
    try:
        agent = CsvAnalysisAgent()
        if use_llm:
            text = agent.analyze_with_llm(path)
            print(text)
        else:
            analysis = agent.analyze_csv_columns(path)
            print(agent.format_analysis(analysis))
        return 0
    except Exception as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(_main())
