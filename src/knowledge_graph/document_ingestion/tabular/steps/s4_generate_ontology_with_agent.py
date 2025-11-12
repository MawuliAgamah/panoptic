"""Step that invokes an agent to analyze a CSV and produce analysis text."""

from __future__ import annotations

import logging
import json
from ...document_pipeline import DocumentPipelineContext, PipelineStep

logger = logging.getLogger("knowledgeAgent.pipeline.csv.agent_analyze")

from knowledge_graph.agent.ontology import generate_ontology_from_analysis

class GenerateOntologyWithAgentStep(PipelineStep):
    name = "generate_ontology_with_agent"

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return self.enabled and hasattr(context, "agent_analysis_text") and bool(getattr(context, "agent_analysis_text", None))

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        try:
            analysis_text = getattr(context, "agent_analysis_text", "")
            ontology = generate_ontology_from_analysis(analysis_text)
            setattr(context, "ontology_specification", ontology)
            logger.info("%s: ontology generated", context.document.id)
            logger.info("%s: ontology: %s", context.document.id, json.dumps(ontology, indent=2))
            context.results[self.name] = {
                "ok": True,
                "entities": ontology.get("entities", []),
                "relationships": ontology.get("relationships", []),
            }
        except Exception as exc:
            logger.exception("Generate ontology failed: %s", exc)
            context.results[self.name] = {"ok": False, "error": str(exc)}
        return context

