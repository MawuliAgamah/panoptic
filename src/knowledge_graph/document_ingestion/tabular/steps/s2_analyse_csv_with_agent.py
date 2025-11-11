"""Step that invokes an agent to analyze a CSV and produce analysis text."""

from __future__ import annotations

import logging
from ...document_pipeline import DocumentPipelineContext, PipelineStep

logger = logging.getLogger("knowledgeAgent.pipeline.csv.agent_analyze")

import os

class AnalyseCsvWithAgentStep(PipelineStep):
    name = "agent_analyze_csv"

    def __init__(self, *, sample_rows: int = 30, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)
        self.sample_rows = sample_rows

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        document = context.ensure_document()
        agent = context.services.agent_service
        if agent is None:
            logger.info("Agent service not available; skipping analysis step")
            raise ValueError("Agent service not available")

        try:
            # Determine delimiter from prior CSV profile if available
            delimiter = getattr(getattr(context, "csv_profile", None), "delimiter", ",") or ","

            analysis_text = agent.analyze_with_llm(
                document.file_path,
                sample_rows=self.sample_rows,
                delimiter=delimiter,
            )
            setattr(context, "agent_analysis_text", analysis_text)


            logger.info("%s: agent analysis preview (first %d chars):\n%s%s", document.id,analysis_text)
        

            context.results[self.name] = {
                "ok": True,
                "chars": len(analysis_text),
                "sample_rows": self.sample_rows,
            }
        except Exception as exc:
            logger.exception("Agent analysis failed for %s: %s", document.id, exc)
            context.results[self.name] = {"ok": False, "error": str(exc)}
        return context
