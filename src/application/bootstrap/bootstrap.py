from __future__ import annotations

"""Bootstrap utilities to load settings, configure logging, and build components.

These functions are intentionally light on business logic and avoid heavy side
effects so they can be reused from FastAPI lifespan, CLI tools, and tests.
"""

from typing import Any, Dict, Optional
import logging


def _load_settings() -> Any:
    """load a Settings instance from the domain settings module.

    Expected location: knowledge_graph.settings.settings
    Prefer a call like `load_settings()` or `get_settings()` in that module.

    Returns the settings object (domain-defined type) or None if unavailable.
    """
    try:
        # Prefer explicit loader
        from knowledge_graph.settings.settings import load_settings  # type: ignore
        return load_settings()
    except Exception:
        pass
    try:
        # Fallback to cached accessor
        from knowledge_graph.settings.settings import get_settings  # type: ignore
        return get_settings()
    except Exception:
        return None


def _configure_logging_from_settings(settings: Any) -> None:
    """Configure root logging once based on settings, if provided.

    If the application already configured logging, this function is a no-op.
    """
    # If root logger already has handlers, assume logging is configured upstream.
    root = logging.getLogger()
    if root.handlers:
        return

    level_name = getattr(getattr(settings, "core", settings), "log_level", "INFO")
    level = getattr(logging, str(level_name).upper(), logging.INFO)
    logging.basicConfig(level=level, format='%(asctime)s | %(levelname)s | %(name)s | %(message)s')


def build_components(
    *,
    settings: Optional[Any] = None,
    attach_to_app: Optional[Any] = None,
) -> Dict[str, Any]:
    """Build the core components and return them as a dict.

    This function prefers domain settings if available; otherwise it falls back
    to a sensible default client using the existing helper in knowledge_graph.

    - Loads settings if not supplied
    - Configures logging (only if not already configured)
    - Instantiates KnowledgeGraphClient (using existing factory)
    - Returns a dict with useful references for the application
    - Optionally attaches the client to a FastAPI app via app.state.kg_client
    """
    resolved_settings = settings or _load_settings()
    _configure_logging_from_settings(resolved_settings)

    # Build client using existing convenience creator to avoid deep refactors
    from knowledge_graph import create_json_client  # type: ignore

    kb_backend = None
    kb_location = None
    try:
        kb = getattr(resolved_settings, "kb_store", None)
        kb_backend = getattr(kb, "backend", None)
        kb_location = getattr(kb, "location", None)
    except Exception:
        kb_backend = None
        kb_location = None

    client = create_json_client(
        data_file=None,
        openai_api_key=getattr(getattr(resolved_settings, "llm", resolved_settings), "api_key", None),
        kb_store_backend=kb_backend,
        kb_store_location=kb_location,
    )

    components: Dict[str, Any] = {
        "settings": resolved_settings,
        "client": client,
        # Expose internals for now to keep wiring pragmatic without refactors
        "db_client": getattr(client, "db_client", None),
        "kb_repo": getattr(client, "_kb_repo", None),
        "llm_service": getattr(client, "llm_service", None),
        "kg_service": getattr(client, "knowledge_graph_service", None),
        "pipeline_config": getattr(client, "pipeline_config", None),
    }

    if attach_to_app is not None:
        try:
            setattr(getattr(attach_to_app, "state"), "kg_client", client)
        except Exception:
            # Be defensive; do not fail startup due to attach issues
            pass

    return components


def shutdown_components(components: Dict[str, Any]) -> None:
    """Best-effort shutdown of long-lived resources created in build_components."""
    client = components.get("client")
    try:
        if client and hasattr(client, "close"):
            client.close()
    except Exception:
        # Never crash shutdown
        pass

