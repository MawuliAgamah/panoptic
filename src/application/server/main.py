from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import tempfile
import uuid
import os
from typing import Optional
import logging
import sys
from pathlib import Path

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
    title="Simple API Server",
    description="A simple FastAPI server",
    version="1.0.0"
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
    
    # Process with your knowledge graph client
    with create_json_client() as client:
        #kg_data = client.extract_knowledge_graph_json(
        #    document_path=temp_path,
        #    document_id=document_id,
        #    domain=domain,
        #    tags=tag_list)
        client.add_document(document_path=temp_path, document_id=document_id, document_type="pdf")
    
    # Count Results 
    #entities_count = len(kg_data.get('entities', []))
    #relationships_count = len(kg_data.get('relationships', []))
    
   #  logger.info(f"Extracted {entities_count} entities and {relationships_count} relationships")
    
    # Return complete results
    return {
        "success": True,
        "message": f"Knowledge graph extracted from {file.filename}",
        "document_id": document_id,
        "filename": file.filename,
        "content_type": file.content_type,
        # "domain": domain,
        # "tags": tag_list,
        # "extraction_stats": {
        #     "entities_count": entities_count,
        #     "relationships_count": relationships_count,
        #     "processing_strategy": kg_data.get('metadata', {}).get('processing_strategy', 'unknown')
        # },
        # "knowledge_graph": kg_data
    }

# Run the server
if __name__ == "__main__":    
    uvicorn.run(
        app,
        host="0.0.0.0",  
        port=8001,
        reload=True     
    )

