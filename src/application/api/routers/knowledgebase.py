from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List

from knowledge_graph.api.client import KnowledgeGraphClient
from ..deps import get_kg_client


router = APIRouter(tags=["knowledgebase"])


class CreateKnowledgeBaseRequest(BaseModel):
    name: str
    owner_id: Optional[str] = None
    description: Optional[str] = None


@router.post("/api/knowledgebases")
def create_knowledgebase(
    payload: CreateKnowledgeBaseRequest,
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    """Create a new knowledge base (idempotent on owner_id+slug)."""
    handle = client.create_knowledgebase(
        name=payload.name,
        owner_id=payload.owner_id,
        description=payload.description,
    )
    # Retrieve full model from registry for richer fields
    items = client.list_knowledgebases(owner_id=payload.owner_id)
    kb = next((it for it in items if it.id == handle.id), None)
    data = kb.model_dump() if kb else {
        "id": handle.id,
        "name": handle.name,
        "slug": handle.slug,
        "owner_id": handle.owner_id,
    }
    return {"success": True, "knowledgebase": data}


@router.get("/api/knowledgebases/{id_or_name}")
def get_knowledgebase(
    id_or_name: str,
    owner_id: Optional[str] = Query(default=None),
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    """Get a knowledge base by id, slug, or exact name."""
    try:
        handle = client.get_knowledgebase(id_or_name, owner_id=owner_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # Retrieve full model if available
    items = client.list_knowledgebases(owner_id=owner_id)
    kb = next((it for it in items if it.id == handle.id), None)
    data = kb.model_dump() if kb else {
        "id": handle.id,
        "name": handle.name,
        "slug": handle.slug,
        "owner_id": handle.owner_id,
    }
    return data


@router.get("/api/knowledgebases")
def list_knowledgebases(
    owner_id: Optional[str] = Query(default=None),
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    """List all knowledge bases, optionally filtered by owner_id."""
    items = client.list_knowledgebases(owner_id=owner_id)
    return {"items": [it.model_dump() for it in items], "count": len(items)}

