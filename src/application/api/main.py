from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from typing import Optional
import logging
from logging.handlers import RotatingFileHandler
import sys
import os
from pathlib import Path
 

# Add the src directory to Python path
current_dir = Path(__file__).parent  # src/application/server/
src_dir = current_dir.parent.parent  # src/
sys.path.insert(0, str(src_dir))



# Set up logging (console + rotating file) early for server logs
logger = logging.getLogger(__name__)
try:
    from knowledge_graph.core.logging_utils import InjectContextFilter
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Compute logs path; honor KG_LOG_FILE if provided
    log_file_env = os.getenv('KG_LOG_FILE')
    if log_file_env:
        log_path = Path(log_file_env)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_file = log_path
    else:
        project_root = Path(__file__).resolve().parents[3]
        logs_dir = project_root / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)
        log_file = logs_dir / 'app.log'

    formatter = logging.Formatter('%(asctime)s | %(levelname)s | %(name)s | doc=%(doc_id)s run=%(run_id)s | %(message)s')

    # Console handler (if none)
    if not any(isinstance(h, logging.StreamHandler) for h in root_logger.handlers):
        ch = logging.StreamHandler()
        ch.setFormatter(formatter)
        ch.addFilter(InjectContextFilter())
        root_logger.addHandler(ch)

    # File handler (if not already attached to same path)
    if not any(getattr(h, 'baseFilename', None) == str(log_file) for h in root_logger.handlers):
        fh = RotatingFileHandler(str(log_file), maxBytes=10_000_000, backupCount=5, encoding='utf-8')
        fh.setFormatter(formatter)
        fh.addFilter(InjectContextFilter())
        root_logger.addHandler(fh)
except Exception:
    # Fall back to basic config without context if needed
    logging.basicConfig(level=logging.INFO)

from contextlib import asynccontextmanager
from knowledge_graph import create_json_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create a single KnowledgeGraphClient for this process and close it on shutdown."""
    app.state.kg_client = create_json_client()
    try:
        yield
    finally:
        # Be defensive in case close is missing or already closed
        try:
            app.state.kg_client.close()
        except Exception:
            pass


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
