from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

from knowledge_graph.api.client import KnowledgeGraphClient
from knowledge_graph.entity_resolution import EntityResolutionService
from knowledge_graph.entity_resolution import persist as er_persist
from application.api.deps import get_kg_client

router = APIRouter(tags=["graph"])
logger = logging.getLogger(__name__)


class GraphSnapshotPayload(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]


class ERRunPayload(BaseModel):
    doc_ids: Optional[List[str]] = None
    mode: Optional[str] = "incremental"


@router.get("/api/graph")
async def get_graph_snapshot(
    document_id: Optional[str] = None,
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    return client.get_graph_snapshot(document_id=document_id)


@router.post("/api/entity-resolution/run")
async def run_entity_resolution(
    payload: ERRunPayload,
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    svc = EntityResolutionService(client.db_client)
    stats = svc.resolve(
        {"doc_ids": payload.doc_ids} if payload.doc_ids else None,
        mode=payload.mode or "incremental",
    )
    return {
        "success": True,
        "mentions_loaded": stats.mentions_loaded,
        "blocks": stats.blocks,
        "canonicals": stats.resolved_entities_upserted,
        "mapped_mentions": stats.mapped_mentions,
        "edges_upserted": stats.edges_upserted,
        "rel_mentions_inserted": stats.rel_mentions_inserted,
    }


@router.get("/api/graph/resolved")
async def get_resolved_graph(
    doc_ids: Optional[str] = None,
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    ids_list: Optional[List[str]] = None
    if doc_ids:
        ids_list = [s for s in (doc_ids.split(",") if doc_ids else []) if s]
    # Build resolved nodes/edges
    resolved = er_persist.fetch_resolved_graph_snapshot(client.db_client, ids_list)
    # Reuse existing documents list to keep UI filter consistent
    raw_snapshot = client.get_graph_snapshot()
    return {
        "nodes": resolved.get("nodes", []),
        "edges": resolved.get("edges", []),
        "documents": raw_snapshot.get("documents", []),
    }


@router.post("/api/graph/save")
async def save_graph_snapshot(payload: GraphSnapshotPayload):
    logger.info(
        "Received graph snapshot save request",
        extra={
            "node_count": len(payload.nodes),
            "edge_count": len(payload.edges),
            "document_count": len(payload.documents),
        },
    )
    return {"success": True}
