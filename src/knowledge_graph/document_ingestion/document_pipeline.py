"""Core orchestration logic for the document processing pipeline."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from ..data_structs.document import Document
from ..core.logging_utils import set_logging_context, clear_logging_context


logger = logging.getLogger("knowledgeAgent.pipeline")


class DocumentPipelineError(Exception):
    """Raised when a pipeline step fails irrecoverably."""


@dataclass
class DocumentPipelineParams:
    """Immutable parameters supplied when running the pipeline."""

    document_path: str
    document_id: str
    domain: Optional[str] = None
    tags: Optional[List[str]] = None


@dataclass
class DocumentPipelineContext:
    """Mutable context shared across pipeline steps."""

    params: DocumentPipelineParams
    services: "DocumentPipelineServices"
    document: Optional[Document] = None
    results: Dict[str, Any] = field(default_factory=dict)

    def set_document(self, document: Document) -> None:
        self.document = document

    def ensure_document(self) -> Document:
        if not self.document:
            raise DocumentPipelineError("Pipeline step requires a document, but none is loaded yet.")
        return self.document


@dataclass
class DocumentPipelineConfig:
    """Configuration toggles determining which steps run."""

    enable_enrichment: bool = True
    enable_kg_extraction: bool = True
    enable_persistence: bool = True
    chunk_size: int = 1000
    chunk_overlap: int = 200

    chunker_type: str = "auto"


@dataclass
class DocumentPipelineServices:
    """External services required by pipeline steps."""

    llm_service: Optional[Any] = None
    kg_service: Optional[Any] = None
    db_client: Optional[Any] = None
    llm_provider: str = "openai"
    agent_service: Optional[Any] = None


class PipelineStep:
    """Base class for pipeline steps."""

    name: str = "pipeline_step"

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def should_run(self, context: DocumentPipelineContext) -> bool:
        return self.enabled

    def run(self, context: DocumentPipelineContext) -> DocumentPipelineContext:
        raise NotImplementedError("Pipeline steps must implement 'run'")


class DocumentPipeline:
    """High-level orchestrator coordinating the configured pipeline steps."""

    def __init__(
        self,
        services: DocumentPipelineServices,
        *,
        config: Optional[DocumentPipelineConfig] = None,
        steps: Optional[List[PipelineStep]] = None,
    ) -> None:
        self.services = services
        self.config = config or DocumentPipelineConfig()
        self._steps = steps or []

    @property
    def steps(self) -> List[PipelineStep]:
        return self._steps

    @steps.setter
    def steps(self, value: List[PipelineStep]) -> None:
        self._steps = value

    def add_step(self, step: PipelineStep) -> None:
        self._steps.append(step)

    def run(
        self,
        *,
        document_path: str,
        document_id: str,
        domain: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[Document]:
        """Execute the configured steps and return the processed document."""
        params = DocumentPipelineParams(
            document_path=document_path,
            document_id=document_id,
            domain=domain,
            tags=tags or [],
        )
        context = DocumentPipelineContext(params=params, services=self.services)

        # Establish a run_id for correlation and inject into logging context
        run_id = str(uuid.uuid4())
        set_logging_context(document_id, run_id)
        context.results["run"] = {"run_id": run_id}

        logger.info("Starting document pipeline for %s", document_path)

        import time
        try:
            for step in self.steps:
                if not step.should_run(context):
                    logger.debug("Skipping disabled step '%s'", step.name)
                    continue

                logger.info("→ Running pipeline step '%s'", step.name)
                try:
                    start_ts = time.time()
                    context = step.run(context)
                    elapsed_ms = int((time.time() - start_ts) * 1000)
                except DocumentPipelineError:
                    # Propagate explicit pipeline errors without wrapping to preserve context.
                    logger.exception("Pipeline step '%s' failed", step.name)
                    raise
                except Exception as exc:  # pragma: no cover - defensive guard
                    logger.exception("Unexpected error during step '%s': %s", step.name, exc)
                    raise DocumentPipelineError(f"Step '{step.name}' failed") from exc
                else:
                    summary = context.results.get(step.name)
                    if isinstance(summary, dict):
                        summary["elapsed_ms"] = summary.get("elapsed_ms", 0) or elapsed_ms
                        context.results[step.name] = summary
                    if summary:
                        logger.info("✓ Step '%s' summary: %s", step.name, summary)
                    else:
                        logger.info("✓ Step '%s' completed", step.name)

            # Report route decision if available
            route_info = context.results.get("route_document", {})
            if route_info:
                logger.info("Routing: %s", route_info)

            logger.info(
                "Document pipeline finished for %s with document id %s",
                document_path,
                context.document.id if context.document else "unknown",
            )
            return context.document
        finally:
            # Clear correlation context to avoid leaking across runs
            clear_logging_context()
