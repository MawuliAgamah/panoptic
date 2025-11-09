from fastapi import Request

# Local import type for clarity; avoids heavy imports at import-time
from knowledge_graph.api.client import KnowledgeGraphClient

def get_kg_client(request: Request) -> KnowledgeGraphClient:
    """Return the shared KnowledgeGraphClient stored on app.state.

    Assumes the FastAPI app configured a lifespan/startup to set `app.state.kg_client`.
    """
    client = getattr(request.app.state, "kg_client", None)
    if client is None:
        raise RuntimeError("KnowledgeGraphClient is not initialized on app.state.kg_client")
    return client

