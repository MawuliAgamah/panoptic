from fastapi import Request
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # Only imported for type checkers; avoids runtime circulars
    from knowledge_graph.api.client import KnowledgeGraphClient  # pragma: no cover


def get_kg_client(request: Request) -> "KnowledgeGraphClient":
    """Return the shared KnowledgeGraphClient stored on app.state.

    Assumes the FastAPI app configured a lifespan/startup to set `app.state.kg_client`.
    """
    client = getattr(request.app.state, "kg_client", None)
    if client is None:
        raise RuntimeError("KnowledgeGraphClient is not initialized on app.state.kg_client")
    return client
