from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import tempfile
import uuid
import os
from typing import Optional, Dict, List, Any
import logging
import sys
from pathlib import Path
from pydantic import BaseModel, Field
import json

# Add the src directory to Python path
current_dir = Path(__file__).parent  # src/application/server/
src_dir = current_dir.parent.parent  # src/
sys.path.insert(0, str(src_dir))


from knowledge_graph import create_json_client

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="KG Extract Backend",
    description="Backend APIs supporting the KG Extract demo",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Basic routes
@app.get("/")
async def root():
    return {"message": "Hello World! Your FastAPI server is running!"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Server is running properly"}

@app.get("/api/test")
async def test_endpoint():
    return {"data": "This is a test endpoint", "success": True}

# Add a simple POST endpoint
@app.post("/api/echo")
async def echo_message(message: dict):
    return {"echo": message, "received_at": "now"}

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


class GraphSnapshotPayload(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    documents: List[Dict[str, Any]]


@app.post("/api/documents/register")
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


@app.get("/api/documents")
async def list_registered_documents():
    return {
        "count": len(registered_documents),
        "items": [doc.model_dump(by_alias=True) for doc in registered_documents.values()],
    }


@app.delete("/api/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and its graph data."""
    with create_json_client() as client:
        client.delete_document(document_id)

    if document_id in registered_documents:
        registered_documents.pop(document_id, None)

    return {"success": True, "document_id": document_id}


@app.get("/api/graph")
async def get_graph_snapshot(document_id: Optional[str] = None):
    """Return the current graph snapshot, optionally filtered by document."""
    with create_json_client() as client:
        snapshot = client.get_graph_snapshot(document_id=document_id)
    return snapshot


@app.post("/api/graph/save")
async def save_graph_snapshot(payload: GraphSnapshotPayload):
    """Accept a client-provided snapshot. Currently acts as a no-op acknowledgment."""
    logger.info(
        "Received graph snapshot save request", extra={
            "node_count": len(payload.nodes),
            "edge_count": len(payload.edges),
            "document_count": len(payload.documents),
        }
    )
    return {"success": True}

# Extract the knowledge graph from the uploaded document
@app.post("/api/extract-kg")
async def extract_knowledge_graph(
    file: UploadFile = File(...),
    document_id: Optional[str] = Form(None),
    domain: Optional[str] = Form("general"),
    tags: Optional[str] = Form("[]")
    ):
    """Extract knowledge graph from uploaded document"""
    
    # Generate document ID if not provided
    if not document_id:
        document_id = f"doc_{uuid.uuid4().hex[:8]}"
    
    # Parse tags from JSON string
    import json
    tag_list = json.loads(tags) if tags else []
    
    logger.info(f"Processing document: {file.filename}")
    
    # Create temporary file for processing
    temp_dir = tempfile.gettempdir()
    temp_filename = f"upload_{uuid.uuid4().hex}_{file.filename}"
    temp_path = os.path.join(temp_dir, temp_filename)
    
    # Save uploaded file to temporary location
    with open(temp_path, 'wb') as temp_file:
        content = await file.read()
        temp_file.write(content)
    
    logger.info(f"Saved file to: {temp_path}")

    try:
        with create_json_client() as client:
            processed_id = client.add_document(
                document_path=temp_path,
                document_id=document_id,
                document_type="pdf",
                domain=domain,
                tags=tag_list,
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

    response_data = {
        "success": True,
        "message": f"Knowledge graph extracted from {file.filename}",
        "document_id": document_id,
        "filename": file.filename,
        "content_type": file.content_type,
        "kg_data": kg_data,
        "entity_count": entity_count,
        "relation_count": relation_count,
        "graph": graph_snapshot,
    }

    logger.info(
        "Extraction complete",
        extra={"entities": entity_count, "relations": relation_count, "document_id": document_id},
    )

    return response_data

# Run the server
# In src/application/server/main.py, change the uvicorn.run call:
if __name__ == "__main__":    
    import sys
    from pathlib import Path
    
    # Add project root to Python path when running from server directory
    current_dir = Path(__file__).parent  
    project_root = current_dir.parent.parent.parent 
    sys.path.insert(0, str(project_root))
    
    uvicorn.run(
        "src.application.server.main:app",  
        host="0.0.0.0",  
        port=8001,
        reload=True  
    )
