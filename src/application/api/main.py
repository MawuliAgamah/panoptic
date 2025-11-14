from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional
import logging
import sys
from pathlib import Path
 

# Add the src directory to Python path
current_dir = Path(__file__).parent  # src/application/server/
src_dir = current_dir.parent.parent  # src/
sys.path.insert(0, str(src_dir))



# Set up logging (console + rotating file) early for server logs
# This MUST happen before any other imports that create loggers
from knowledge_graph.logging_utils import setup_logging

# Configure logging immediately - before any other imports
# Pass project root explicitly for accurate log file location
project_root = Path(__file__).resolve().parents[3]
setup_logging(project_root=project_root)
logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from knowledge_graph import create_client
from knowledge_graph.settings.settings import Settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create a single KnowledgeGraphClient and close it on shutdown (no bootstrap)."""
    app.state.kg_client = create_client(settings=Settings())
    try:
        yield
    finally:
        app.state.kg_client.close()


# Create FastAPI app
app = FastAPI(
    title="KG Extract Backend",
    description="Backend APIs supporting the KG Extract demo",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include feature routers
from .routers import documents as documents_router
from .routers import graph as graph_router
from .routers import knowledgebase as knowledgebase_router
app.include_router(documents_router.router)
app.include_router(graph_router.router)
app.include_router(knowledgebase_router.router)

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


if __name__ == "__main__":    
    import sys
    from pathlib import Path
    
    # Add project root to Python path when running from server directory
    current_dir = Path(__file__).parent  
    project_root = current_dir.parent.parent.parent 
    sys.path.insert(0, str(project_root))
    
    uvicorn.run(
        "application.api.main:app",
        host="0.0.0.0",
        port=8001,
        reload=True
    )
