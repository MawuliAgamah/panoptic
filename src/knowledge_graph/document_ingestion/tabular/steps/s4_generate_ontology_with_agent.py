"""Step that invokes an agent to analyze a CSV and produce analysis text."""

from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from typing import Dict, Any, Optional
from ...document_pipeline import DocumentPipelineContext, PipelineStep
from knowledge_graph.logging_utils import green
from knowledge_graph.persistence.sqlite.sql_lite import SqlLite
from knowledge_graph.settings.settings import get_settings
from knowledge_graph.logging_utils import green
logger = logging.getLogger("knowledgeAgent.pipeline.csv.agent_analyze")

from knowledge_graph.agent.ontology import generate_ontology_from_analysis


@dataclass
class DocumentOntology:
    """Document ontology data structure matching the database schema."""
    document_id: int
    specification: Dict[str, Any]  # JSON payload
    status: str = 'proposed'  # 'proposed', 'approved', 'rejected', 'active'
    version: int = 1
    proposed_by: Optional[str] = None
    reviewed_by: Optional[str] = None
    created_at: Optional[str] = None  # ISO timestamp string
    approved_at: Optional[str] = None  # ISO timestamp string
    is_canonical: bool = False  # 0 or 1 in database
    id: Optional[int] = None  # Primary key, set after insert



class GenerateOntologyWithAgentStep(PipelineStep):
    name = "generate_ontology_with_agent"

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return self.enabled and hasattr(context, "agent_analysis_text") and bool(getattr(context, "agent_analysis_text", None))

    def __init__(self, *, enabled: bool = True) -> None:
        super().__init__(enabled=enabled)

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        logger.info(green("\n\n --------------------------------- Step 4: Generate Ontology With Agent--------------------------------- \n\n"))
        try:
            document = context.ensure_document()
            doc_id = document.id
                    # Generate ontology from analysis
            analysis_text = getattr(context, "agent_analysis_text", "")

            ontology = generate_ontology_from_analysis(analysis_text)
            
            entities_count = len(ontology.get("entities", []))
            relationships_count = len(ontology.get("relationships", []))
            logger.info(f"Ontology generated: {entities_count} entities, {relationships_count} relationships")
            
            setattr(context, "ontology_specification", ontology)
            context.results[self.name] = {
                "ok": True,
                "entities": ontology.get("entities", []),
                "relationships": ontology.get("relationships", []),
            }
                        

            doc_id_int = int(document.id)

            doc_ontology = DocumentOntology(
                document_id=doc_id_int,
                specification=ontology,
                status='proposed',
                version=1,
                is_canonical=False
            )
            
            sqlite = SqlLite(settings=get_settings())
            doc_repo = sqlite.tabular_document_repository()
            saved_ontology = doc_repo.save_document_ontology(doc_ontology)
            
        except Exception as exc:
            logger.exception(f"❌ [STEP 4] Generate ontology failed: {exc}")
            context.results[self.name] = {"ok": False, "error": str(exc)}
        return context

