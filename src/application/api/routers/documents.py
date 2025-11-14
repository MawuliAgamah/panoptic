from __future__ import annotations

from fastapi import APIRouter, UploadFile, File, Form, Depends
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
import json
import uuid
import tempfile
import time
import logging

from application.api.deps import get_kg_client

router = APIRouter(tags=["documents"])


class DocumentRegistration(BaseModel):
    document_id: str = Field(..., alias="document_id")
    title: str
    source: str
    mime_type: Optional[str] = Field(default=None, alias="mime_type")
    author: Optional[str] = None
    external_id: Optional[str] = Field(default=None, alias="external_id")
    url: Optional[str] = None
    description: Optional[str] = None


registered_documents: Dict[str, DocumentRegistration] = {}
logger = logging.getLogger(__name__)


@router.post("/api/documents/register")
async def register_document(payload: DocumentRegistration):
    registered_documents[payload.document_id] = payload
    logger.info(
        "Registered remote document",
        extra={
            "document_id": payload.document_id,
            "source": payload.source,
            "external_id": payload.external_id,
        },
    )
    return {
        "success": True,
        "document_id": payload.document_id,
        "message": "Document metadata stored.",
    }


@router.get("/api/documents")
async def list_registered_documents():
    return {
        "count": len(registered_documents),
        "items": [doc.model_dump(by_alias=True) for doc in registered_documents.values()],
    }


"""Simple in-memory mapping of KB -> documents for association demos."""
knowledgebase_documents: Dict[str, List[str]] = {}


@router.post("/api/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    knowledgebase_id: Optional[str] = Form(None),
    client = Depends(get_kg_client),
):
    """Upload a document and (optionally) associate it with a knowledge base.

    Returns the pipeline-generated document id as `document_id`.
    """
    logger.info("Uploading document: %s", file.filename)

    # Save to a temporary file to pass a path to the pipeline
    import uuid as _uuid, os, tempfile
    tmp_dir = tempfile.gettempdir()
    tmp_path = os.path.join(tmp_dir, f"upload_{_uuid.uuid4().hex}_{file.filename}")
    content = await file.read()
    with open(tmp_path, "wb") as tmp:
        tmp.write(content)

    processed_id: Optional[str] = None
    try:
        # Ingest using the convenience method, which returns the processed id
        processed_id = client.upload_file(tmp_path, kb_id=knowledgebase_id)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass

    if not processed_id:
        return {"success": False, "message": "Upload failed"}

    # Link to KB (in-memory demo association)
    if knowledgebase_id:
        knowledgebase_documents.setdefault(knowledgebase_id, [])
        if processed_id not in knowledgebase_documents[knowledgebase_id]:
            knowledgebase_documents[knowledgebase_id].append(processed_id)
        logger.info(
            "Associated document with KB",
            extra={"kb_id": knowledgebase_id, "document_id": processed_id},
        )

    return {
        "success": True,
        "message": "Document uploaded successfully",
        "document_id": processed_id,  # pipeline id
        "submitted_document_id": document_id,
        "knowledgebase_id": knowledgebase_id,
        "filename": file.filename,
        "content_type": file.content_type,
    }


@router.delete("/api/documents/{document_id}")
async def delete_document(
    document_id: str,
    client = Depends(get_kg_client),
):
    """Delete a document and its graph data."""
    client.delete_document(document_id)

    if document_id in registered_documents:
        registered_documents.pop(document_id, None)

    return {"success": True, "document_id": document_id}


@router.post("/api/extract-kg")
async def extract_knowledge_graph(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    domain: Optional[str] = Form("general"),
    tags: Optional[str] = Form("[]"),
    client = Depends(get_kg_client),
):
    """Extract knowledge graph from uploaded document (generic)."""

    # Generate document ID if not provided
    if not document_id:
        document_id = f"doc_{uuid.uuid4().hex[:8]}"

    # Parse tags from JSON string
    tag_list = json.loads(tags) if tags else []

    logger.info("Processing document: %s", file.filename)

    # Create temporary file for processing
    temp_dir = tempfile.gettempdir()
    temp_filename = f"upload_{uuid.uuid4().hex}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)

    # Save uploaded file to temporary location
    with open(temp_path, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)

    logger.info("Saved file to: %s", temp_path)

    try:
        processed_id = client.add_document(
            document_path=temp_path,
        )

        graph_snapshot = client.get_graph_snapshot(document_id=processed_id)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            logger.warning("Failed to remove temporary file %s", temp_path)

    id_to_label = {node["id"]: node["label"] for node in graph_snapshot.get("nodes", [])}
    kg_data = {
        "entities": [node["label"] for node in graph_snapshot.get("nodes", [])],
        "relations": [
            [
                id_to_label.get(edge.get("source"), edge.get("source")),
                edge.get("predicate"),
                id_to_label.get(edge.get("target"), edge.get("target")),
            ]
            for edge in graph_snapshot.get("edges", [])
        ],
    }

    entity_count = len(graph_snapshot.get("nodes", []))
    relation_count = len(graph_snapshot.get("edges", []))

    return {
        "success": True,
        "message": f"Knowledge graph extracted from {file.filename}",
        "document_id": processed_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "kg_data": kg_data,
        "entity_count": entity_count,
        "relation_count": relation_count,
        "graph": graph_snapshot,
    }


@router.post("/api/documents/upload-csv")
async def upload_csv_document(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    kb_id: Optional[str] = Form(None),
    client = Depends(get_kg_client),
):
    """Upload a CSV file, build a knowledge graph via the CSV pipeline route, and return a snapshot."""
    # Validate file looks like CSV
    fname = file.filename or ""
    ctype = (file.content_type or "").lower()
    if not (fname.lower().endswith(".csv") or ctype in {"text/csv", "application/vnd.ms-excel"}):
        return {
            "success": False,
            "error": "Uploaded file is not recognized as CSV",
            "filename": fname,
            "content_type": file.content_type,
        }

    # Generate a doc id if none provided
    if not document_id:
        document_id = f"doc_{uuid.uuid4().hex[:8]}"

    # Save to a temporary file
    temp_dir = tempfile.gettempdir()
    temp_filename = f"upload_{uuid.uuid4().hex}_{fname or 'data.csv'}"
    temp_path = os.path.join(temp_dir, temp_filename)
    with open(temp_path, "wb") as tmp:
        content = await file.read()
        tmp.write(content)
    logger.info("[csv] Saved CSV to %s (%d bytes)", temp_path, len(content))

    # Parse tags from JSON string
    try:
        processed_id = client.upload_file(temp_path, kb_id=kb_id)
        snapshot = client.get_graph_snapshot(document_id=processed_id)
    finally:
        try:
            os.remove(temp_path)
        except OSError:
            logger.warning("[csv] Failed to remove temp file %s", temp_path)

    # Map node ids to labels for a simplified kg_data view
    id_to_label = {node.get("id"): node.get("label") for node in snapshot.get("nodes", [])}
    kg_data = {
        "entities": [node.get("label") for node in snapshot.get("nodes", [])],
        "relations": [
            [
                id_to_label.get(edge.get("source"), edge.get("source")),
                edge.get("predicate"),
                id_to_label.get(edge.get("target"), edge.get("target")),
            ]
            for edge in snapshot.get("edges", [])
        ],
    }

    return {
        "success": True,
        "message": f"CSV ingested: {fname}",
        "document_id": processed_id,
        "filename": fname,
        "content_type": file.content_type,
        "entity_count": len(snapshot.get("nodes", [])),
        "relation_count": len(snapshot.get("edges", [])),
        "kg_data": kg_data,
        "graph": snapshot,
    }


class BulkDirRequest(BaseModel):
    dir: str
    glob: Optional[str] = Field(default="**/*.md")
    domain: Optional[str] = None
    tags: Optional[List[str]] = None
    concurrency: Optional[int] = 1
    skip_existing: Optional[bool] = True


@router.post("/api/extract-kg/bulk")
async def extract_knowledge_graph_bulk(
    files: List[UploadFile] = File(...),
    domain: Optional[str] = Form("general"),
    tags: Optional[str] = Form("[]"),
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    """Bulk extract knowledge graphs from multiple uploaded files."""
    # Parse tags from JSON string
    tag_list = json.loads(tags) if tags else []

    temp_dir = tempfile.gettempdir()
    results: List[Dict[str, Any]] = []
    success = 0
    failed = 0

    for uf in files:
            start_ts = time.time()
            temp_path = os.path.join(temp_dir, f"upload_{uuid.uuid4().hex}_{uf.filename}")
            try:
                content = await uf.read()
                with open(temp_path, "wb") as tmp:
                    tmp.write(content)

                # Let client infer type; generate a doc id
                doc_id = f"doc_{uuid.uuid4().hex[:8]}"
                logger.info("[bulk] Saved file %s to %s (size=%d)", uf.filename, temp_path, len(content))

                processed_id = client.add_document(
                    document_path=temp_path,
                )

                elapsed_ms = int((time.time() - start_ts) * 1000)
                results.append(
                    {
                        "filename": uf.filename,
                        "path": temp_path,
                        "document_id": processed_id,
                        "ok": True,
                        "elapsed_ms": elapsed_ms,
                    }
                )
                success += 1
                logger.info("[bulk] Done %s -> %s (%d ms)", uf.filename, processed_id, elapsed_ms)
            except Exception as exc:
                elapsed_ms = int((time.time() - start_ts) * 1000)
                logger.exception("[bulk] Error processing %s (%d ms): %s", uf.filename, elapsed_ms, exc)
                results.append(
                    {
                        "filename": uf.filename,
                        "path": temp_path,
                        "ok": False,
                        "error": str(exc),
                        "elapsed_ms": elapsed_ms,
                    }
                )
                failed += 1
            finally:
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except OSError:
                    pass

    logger.info("[bulk] Completed multi-file ingestion: success=%d failed=%d", success, failed)
    # Return minimal graph snapshot so the UI can eagerly refresh if desired
    try:
        snapshot = client.get_graph_snapshot()
    except Exception:
        snapshot = {"nodes": [], "edges": [], "documents": []}

    return {"success": failed == 0, "processed": success, "failed": failed, "results": results, "graph": snapshot}


@router.post("/api/extract-kg/bulk-dir")
async def extract_knowledge_graph_bulk_dir(
    payload: BulkDirRequest,
    client: KnowledgeGraphClient = Depends(get_kg_client),
):
    """Bulk ingest documents from a server-side directory path (admin/local use)."""
    import time as _time
    started = _time.time()
    results = client.bulk_add_documents(
            payload.dir,
            glob=payload.glob or "**/*.md",
            domain=payload.domain,
            tags=payload.tags,
            concurrency=payload.concurrency or 1,
            skip_existing=bool(payload.skip_existing),
            force_structured_markdown=True,
        )
    ok = sum(1 for r in results if r.get("ok"))
    skipped = sum(1 for r in results if r.get("skipped"))
    failed = sum(1 for r in results if (not r.get("ok") and not r.get("skipped")))
    elapsed_ms = int((_time.time() - started) * 1000)
    logger.info("[bulk-dir] Summary: ok=%d skipped=%d failed=%d (%d ms)", ok, skipped, failed, elapsed_ms)
    snapshot = client.get_graph_snapshot()
    return {
        "success": failed == 0,
        "ok": ok,
        "skipped": skipped,
        "failed": failed,
        "elapsed_ms": elapsed_ms,
        "results": results,
        "graph": snapshot,
    }
