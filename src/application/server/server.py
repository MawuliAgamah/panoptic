#!/usr/bin/env python3
"""FastAPI web server for knowledge graph visualization and document upload"""

import asyncio
import os
import json
import uuid
import tempfile
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Any
import logging

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

import sys
from pathlib import Path

# Add the src directory to Python path
current_dir = Path(__file__).parent  # src/application/server/
src_dir = current_dir.parent.parent  # src/
sys.path.insert(0, str(src_dir))

from knowledge_graph import create_json_client
from flashcards import create_flashcard_client
from flashcards.models import KG_Mapping

logger = logging.getLogger(__name__)

class WebServer:
    def __init__(self):
        self.app = FastAPI(
            title="Knowledge Graph Web Interface",
            description="Upload documents, visualize knowledge graphs, and manage flashcards",
            version="1.0.0"
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Initialize services
        self.flashcard_client = None
        self.setup_routes()
        self.setup_static_files()

    def setup_static_files(self):
        """Setup static file serving for the visualization"""
        # Get the frontend directory path (where our components are) - use absolute paths
        current_dir = Path(__file__).parent.resolve()
        frontend_dir = current_dir.parent / "frontend"

        # Also check for legacy vis directory in src
        project_root = current_dir.parent.parent
        vis_dir = project_root / "vis"

        logger.info(f"Setting up static files from: {frontend_dir}")
        logger.info(f"Frontend directory exists: {frontend_dir.exists()}")

        # Mount frontend directory as /frontend for static file access
        if frontend_dir.exists():
            self.app.mount("/frontend", StaticFiles(directory=str(frontend_dir)), name="frontend")
            logger.info(f"✅ Mounted frontend directory as /frontend: {frontend_dir}")
        elif vis_dir.exists():
            self.app.mount("/vis", StaticFiles(directory=str(vis_dir)), name="vis")
            logger.info(f"✅ Mounted legacy vis directory: {vis_dir}")
        else:
            logger.error(f"❌ Neither frontend nor vis directory found: {frontend_dir}, {vis_dir}")
            logger.error(f"Current working directory: {Path.cwd()}")
            logger.error(f"Server file location: {current_dir}")

    def setup_routes(self):
        """Setup all API routes"""

        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve the main visualization page with modular components"""
            # Use absolute path resolution to avoid working directory issues
            current_dir = Path(__file__).parent.resolve()
            frontend_dir = current_dir.parent / "frontend"
            index_path = frontend_dir / "index.html"

            logger.info(f"Looking for index file at: {index_path}")
            logger.info(f"File exists: {index_path.exists()}")

            if index_path.exists():
                logger.info(f"Serving index.html from: {index_path}")
                return FileResponse(str(index_path))
            else:
                # Fallback to legacy version if main not found
                fallback_path = frontend_dir / "index-legacy.html"
                if fallback_path.exists():
                    logger.info(f"Serving legacy index.html from: {fallback_path}")
                    return FileResponse(str(fallback_path))
                else:
                    # Check legacy vis directory
                    project_root = current_dir.parent.parent
                    vis_dir = project_root / "vis"
                    legacy_index = vis_dir / "index.html"

                    logger.warning(f"Index files not found. Checked paths:")
                    logger.warning(f"  - Primary: {index_path}")
                    logger.warning(f"  - Fallback: {fallback_path}")
                    logger.warning(f"  - Legacy: {legacy_index}")

                    if legacy_index.exists():
                        return FileResponse(str(legacy_index))
                    else:
                        return HTMLResponse(f"""
                        <html>
                            <body>
                                <h1>Knowledge Graph Visualization</h1>
                                <p><strong>Debug Info:</strong></p>
                                <ul>
                                    <li>Current working directory: {Path.cwd()}</li>
                                    <li>Server file location: {current_dir}</li>
                                    <li>Frontend directory: {frontend_dir} (exists: {frontend_dir.exists()})</li>
                                    <li>Index path: {index_path} (exists: {index_path.exists()})</li>
                                </ul>
                                <p>Available endpoints:</p>
                                <ul>
                                    <li><a href="/docs">API Documentation</a></li>
                                    <li><a href="/api/health">Health Check</a></li>
                                    <li><a href="/database/knowledge_store.json">Knowledge Graph Data</a></li>
                                </ul>
                            </body>
                        </html>
                        """)

        @self.app.get("/api/health")
        async def health_check():
            """Health check endpoint"""
            return {"status": "healthy", "message": "Knowledge Graph Web Server is running"}

        @self.app.post("/api/hierarchy/node")
        async def create_hierarchy_node(payload: Dict[str, Any]):
            """Create a user node in the knowledge store as a first-class entity using the JSON KG client."""
            try:
                name = payload.get('name')
                node_type = payload.get('type', 'field')
                level = int(payload.get('level', 0))
                parent_id = payload.get('parent_id')
                metadata = payload.get('metadata', {}) or {}
                if not name:
                    raise HTTPException(status_code=400, detail="'name' is required")

                with create_json_client() as client:
                    svc = client.db_client.json_kg_service
                    # Add entity (user-created)
                    entity = svc.add_custom_entity(
                        name=name,
                        entity_type=node_type,
                        metadata={**metadata, 'level': level, 'is_user_created': True, 'parent_id': parent_id}
                    )

                    # If parent_id is provided, link hierarchy
                    if parent_id is not None:
                        # Resolve parent by id or name
                        parent = None
                        try:
                            parent_int = int(parent_id)
                            parent = svc.get_entity_by_id(parent_int)
                        except Exception:
                            parent = svc.get_entity_by_name(str(parent_id))
                        if not parent:
                            raise HTTPException(status_code=404, detail=f"Parent not found: {parent_id}")
                        svc.add_custom_relationship(
                            source_name=parent['name'],
                            relation_type='is_parent_of',
                            target_name=entity['name']
                        )

                    return JSONResponse(content={"node": entity})
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating hierarchy node: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/knowledge-graph/upload")
        async def upload_knowledge_graph_json(payload: Dict[str, Any]):
            """Upload a knowledge graph from JSON data and optionally link to a parent node."""
            try:
                kg_data = payload.get('knowledge_graph', {})
                parent_node_id = payload.get('parent_node_id')
                
                if not kg_data:
                    raise HTTPException(status_code=400, detail="'knowledge_graph' data is required")
                
                with create_json_client() as client:
                    svc = client.db_client.json_kg_service
                    
                    # Add entities and relationships in batch
                    created_entities = svc.add_entities_batch(kg_data.get('entities', []))
                    created_relationships = svc.add_relationships_batch(kg_data.get('relationships', []))
                    
                    entity_ids = [str(entity['id']) for entity in created_entities]
                    relationship_ids = [str(rel['id']) for rel in created_relationships]
                    
                    # Link to parent node if provided
                    parent_relationships_created = 0
                    if parent_node_id and created_entities:
                        try:
                            # Resolve parent by id or name
                            parent = None
                            try:
                                parent = svc.get_entity_by_id(int(parent_node_id))
                            except Exception:
                                parent = svc.get_entity_by_name(str(parent_node_id))
                            
                            if parent:
                                for entity in created_entities:
                                    try:
                                        svc.add_custom_relationship(parent['name'], 'contains', entity['name'])
                                        parent_relationships_created += 1
                                    except Exception as rel_err:
                                        logger.warning(f"Failed to create parent relationship: {rel_err}")
                                
                                logger.info(f"Linked {parent_relationships_created} entities to parent {parent['name']}")
                            else:
                                logger.warning(f"Parent node not found: {parent_node_id}")
                        except Exception as link_err:
                            logger.warning(f"Failed to link entities to parent: {link_err}")
                    
                return JSONResponse(content={
                    "success": True,
                    "message": f"Knowledge graph uploaded successfully",
                    "entities_added": len(created_entities),
                    "relationships_added": len(created_relationships) + parent_relationships_created,
                    "entity_ids": entity_ids,
                    "relationship_ids": relationship_ids,
                    "parent_node_id": parent_node_id
                })
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Failed to upload knowledge graph: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.delete("/api/knowledge-store/clear")
        async def clear_knowledge_store():
            """Clear all data from the knowledge store."""
            try:
                with create_json_client() as client:
                    svc = client.db_client.json_kg_service
                    result = svc.clear_knowledge_store()
                    
                return JSONResponse(content={
                    "success": result['success'],
                    "message": f"Knowledge store cleared successfully" if result['success'] else "Failed to clear knowledge store",
                    "entities_cleared": result['entities_cleared'],
                    "relationships_cleared": result['relationships_cleared'],
                    "entities_remaining": result['entities_remaining'],
                    "relationships_remaining": result['relationships_remaining'],
                    "error": result.get('error')
                })
            except Exception as e:
                logger.error(f"Failed to clear knowledge store: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/hierarchy/link")
        async def create_hierarchy_link(payload: Dict[str, Any]):
            """Create a hierarchy relationship between existing entities (is_parent_of)."""
            try:
                source_id = payload.get('source_id')
                target_id = payload.get('target_id')
                if source_id is None or target_id is None:
                    raise HTTPException(status_code=400, detail="'source_id' and 'target_id' are required")
                with create_json_client() as client:
                    svc = client.db_client.json_kg_service
                    def resolve(val: Any) -> Optional[str]:
                        try:
                            eid = int(val)
                            ent = svc.get_entity_by_id(eid)
                            return ent['name'] if ent else None
                        except Exception:
                            # treat as name
                            return str(val)
                    source_name = resolve(source_id)
                    target_name = resolve(target_id)
                    if not source_name or not target_name:
                        raise HTTPException(status_code=404, detail="Source or target not found")
                    rel = svc.add_custom_relationship(source_name, 'is_parent_of', target_name)
                    return JSONResponse(content={"link": rel})
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error creating hierarchy link: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.get("/api/debug/data")
        async def debug_data():
            """Debug endpoint to test data loading"""
            try:
                current_dir = Path(__file__).parent.resolve()
                project_root = current_dir.parent.parent.parent  # Go up one more level to reach the actual project root
                kg_file = project_root / "database" / "knowledge_store.json"

                result = {
                    "server_location": str(current_dir),
                    "project_root": str(project_root),
                    "kg_file_path": str(kg_file),
                    "kg_file_exists": kg_file.exists(),
                    "working_directory": str(Path.cwd())
                }

                if kg_file.exists():
                    with open(kg_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    result.update({
                        "entities_count": len(data.get('entities', [])),
                        "relationships_count": len(data.get('relationships', [])),
                        "sample_entity": data.get('entities', [{}])[:1]
                    })

                return JSONResponse(content=result)
            except Exception as e:
                return JSONResponse(content={"error": str(e)}, status_code=500)

        @self.app.get("/database/knowledge_store.json")
        async def get_knowledge_graph_data():
            """Serve the knowledge graph data for visualization"""
            try:
                # Get the database path using absolute resolution
                current_dir = Path(__file__).parent.resolve()
                project_root = current_dir.parent.parent.parent  # Go up one more level to reach the actual project root
                kg_file = project_root / "database" / "knowledge_store.json"

                logger.info(f"Looking for knowledge graph data at: {kg_file}")
                logger.info(f"File exists: {kg_file.exists()}")

                if kg_file.exists():
                    with open(kg_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    # Log some stats about the data
                    entities_count = len(data.get('entities', []))
                    relationships_count = len(data.get('relationships', []))
                    logger.info(f"Serving knowledge graph data: {entities_count} entities, {relationships_count} relationships")

                    return JSONResponse(content=data)
                else:
                    logger.warning(f"Knowledge graph file not found at: {kg_file}")
                    logger.warning(f"Directory contents: {list(kg_file.parent.iterdir()) if kg_file.parent.exists() else 'Parent directory does not exist'}")

                    # Return sample data if no knowledge graph exists
                    sample_data = {
                        "entities": [
                            {
                                "id": 1,
                                "name": "Sample Entity",
                                "type": "extracted",
                                "document_ids": ["sample_doc"],
                                "metadata": {"title": "Sample Document"}
                            }
                        ],
                        "relationships": [],
                        "metadata": {
                            "total_entities": 1,
                            "total_relationships": 0,
                            "unique_documents": 1
                        }
                    }
                    logger.info("Serving sample data instead")
                    return JSONResponse(content=sample_data)

            except Exception as e:
                logger.error(f"Error serving knowledge graph data: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # User graph persistence (hierarchical nodes/links created in UI)
        def _user_graph_path() -> Path:
            current_dir = Path(__file__).parent.resolve()
            project_root = current_dir.parent.parent.parent
            db_dir = project_root / "database"
            db_dir.mkdir(parents=True, exist_ok=True)
            return db_dir / "user_graph.json"

        @self.app.get("/api/user-graph")
        async def get_user_graph():
            try:
                path = _user_graph_path()
                if path.exists():
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                else:
                    data = {"nodes": [], "links": []}
                return JSONResponse(content=data)
            except Exception as e:
                logger.error(f"Error reading user graph: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/user-graph")
        async def save_user_graph(payload: Dict[str, Any]):
            try:
                path = _user_graph_path()
                # Basic validation
                nodes = payload.get("nodes", [])
                links = payload.get("links", [])
                to_write = {"nodes": nodes, "links": links}
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(to_write, f, ensure_ascii=False, indent=2)
                return {"success": True}
            except Exception as e:
                logger.error(f"Error saving user graph: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/api/upload-document")
        async def upload_document(
            file: UploadFile = File(...),
            title: str = Form(...),
            type: str = Form(...),
            domain: str = Form(...),
            description: str = Form(""),
            tags: str = Form("[]"),
            auto_extract: bool = Form(True),
            generate_flashcards: bool = Form(False),
            parent_node_id: str = Form(None)
        ):
            """Handle document upload and processing"""
            try:
                # Parse tags from JSON string
                user_tags = json.loads(tags) if tags else []

                logger.info(f"Uploading document: {title}")
                logger.info(f"File: {file.filename} ({file.content_type})")
                logger.info(f"Type: {type}, Domain: {domain}")
                logger.info(f"Tags: {user_tags}")
                logger.info(f"Auto-extract: {auto_extract}, Generate flashcards: {generate_flashcards}")

                # Create temporary file
                temp_dir = Path(tempfile.gettempdir())
                temp_file = temp_dir / f"upload_{uuid.uuid4()}_{file.filename}"

                try:
                    # Save uploaded file
                    with open(temp_file, 'wb') as f:
                        content = await file.read()
                        f.write(content)

                    logger.info(f"Saved temporary file: {temp_file}")

                    # Process with knowledge graph if auto_extract is enabled
                    entities_extracted = 0
                    relationships_created = 0
                    new_entity_ids = []

                    if auto_extract:
                        entities_extracted, relationships_created, new_entity_ids = await self.process_document_kg(
                            str(temp_file), title, type, domain, description, user_tags, parent_node_id
                        )

                    # Generate flashcards if requested
                    flashcards_created = 0
                    if generate_flashcards:
                        flashcards_created = await self.generate_flashcards_from_document(
                            str(temp_file), title, domain, user_tags
                        )

                    return JSONResponse(content={
                        "success": True,
                        "message": f"Document '{title}' uploaded successfully",
                        "document_title": title,
                        "entities_extracted": entities_extracted,
                        "relationships_created": relationships_created,
                        "flashcards_created": flashcards_created,
                        "new_entity_ids": new_entity_ids,
                        "parent_node_id": parent_node_id,
                        "tags": user_tags
                    })

                finally:
                    # Clean up temporary file
                    if temp_file.exists():
                        temp_file.unlink()

            except Exception as e:
                logger.error(f"Document upload error: {e}")
                raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

        @self.app.get("/api/flashcards/stats")
        async def get_flashcard_stats():
            """Get flashcard system statistics"""
            try:
                if not self.flashcard_client:
                    self.flashcard_client = create_flashcard_client(enable_anki=False)

                # Get health check for system status
                health = self.flashcard_client.health_check()
                if not health.success:
                    raise HTTPException(status_code=500, detail=f"Flashcard system unhealthy: {health.error}")

                # For now, return basic stats - could be enhanced to get aggregate user stats
                return JSONResponse(content={
                    "system_status": "healthy",
                    "version": health.data.get("version", "1.0.0"),
                    "anki_integration": health.data.get("services", {}).get("anki_integration", "disabled"),
                    "algorithms_available": ["sm2"]  # Based on current implementation
                })

            except Exception as e:
                logger.error(f"Error getting flashcard stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def process_document_kg(self, file_path: str, title: str, doc_type: str,
                                 domain: str, description: str, user_tags: List[str], parent_node_id: Optional[str] = None) -> tuple[int, int, List[str]]:
        """Process document through knowledge graph extraction and return JSON data"""
        try:
            logger.info(f"Processing document through KG pipeline: {title}")

            # Generate document ID
            doc_id = f"uploaded_{title.replace(' ', '_').replace('.', '_').lower()}_{uuid.uuid4().hex[:8]}"

            # Initialize client and extract KG as JSON (without saving to database)
            with create_json_client() as client:
                # Extract knowledge graph as JSON data
                kg_json = client.extract_knowledge_graph_json(
                    document_path=file_path,
                    document_id=doc_id,
                    document_type=doc_type,
                    domain=domain,
                    tags=user_tags
                )
                
                logger.info(f"Extracted KG JSON: {len(kg_json.get('entities', []))} entities, {len(kg_json.get('relationships', []))} relationships")
                
                # Now add the extracted data to the knowledge store
                svc = client.db_client.json_kg_service
                
                # Add entities in batch
                created_entities = svc.add_entities_batch(kg_json.get('entities', []))
                entity_ids = [str(entity['id']) for entity in created_entities]
                
                # Add relationships in batch  
                created_relationships = svc.add_relationships_batch(kg_json.get('relationships', []))
                
                logger.info(f"Added to knowledge store: {len(created_entities)} entities, {len(created_relationships)} relationships")

                # Link extracted entities to parent node if provided
                if parent_node_id and created_entities:
                    try:
                        # Resolve parent by id or name
                        parent = None
                        try:
                            parent = svc.get_entity_by_id(int(parent_node_id))
                        except Exception:
                            parent = svc.get_entity_by_name(str(parent_node_id))
                        
                        if parent:
                            parent_relationships_created = 0
                            for entity in created_entities:
                                try:
                                    svc.add_custom_relationship(parent['name'], 'contains', entity['name'])
                                    parent_relationships_created += 1
                                    logger.info(f"Created 'contains' relationship: {parent['name']} -> {entity['name']}")
                                except Exception as rel_err:
                                    logger.warning(f"Failed to create relationship {parent['name']} -> {entity['name']}: {rel_err}")
                            
                            logger.info(f"Successfully linked {parent_relationships_created} entities to parent node '{parent['name']}'")
                        else:
                            logger.warning(f"Parent node not found: {parent_node_id}")
                    except Exception as link_err:
                        logger.warning(f"Failed to link extracted entities to parent node: {link_err}")

                entities_extracted = len(created_entities)
                total_relationships_created = len(created_relationships)

                logger.info(f"KG processing complete: {entities_extracted} entities, {total_relationships_created} relationships")
                return entities_extracted, total_relationships_created, entity_ids

        except Exception as e:
            logger.error(f"KG processing error: {e}")
            return 0, 0, []

    async def generate_flashcards_from_document(self, file_path: str, title: str,
                                              domain: str, user_tags: List[str]) -> int:
        """Generate flashcards from uploaded document"""
        try:
            logger.info(f"Generating flashcards from document: {title}")

            if not self.flashcard_client:
                self.flashcard_client = create_flashcard_client(enable_anki=False)

            # Create a sample flashcard from the document
            # TODO: Replace with actual content extraction and multiple cards
            user_id = "web_user"  # You might want to implement user sessions

            # Create or get default deck
            deck_result = self.flashcard_client.create_deck(
                user_id=user_id,
                name=f"{domain.title()} - {title}",
                description=f"Flashcards from uploaded document: {title}",
                algorithm="sm2"
            )

            if not deck_result.success:
                logger.error(f"Failed to create deck: {deck_result.error}")
                return 0

            # Create a sample flashcard based on the document
            card_result = self.flashcard_client.create_card(
                user_id=user_id,
                front=f"What is the main topic of '{title}'?",
                back=f"This document covers {domain} and includes concepts like: {', '.join(user_tags)}",
                domains=[domain] + user_tags  # Using domains instead of tags
            )

            if card_result.success:
                logger.info(f"Created flashcard for document: {title}")
                
                # Optionally create a simple KG mapping for future use
                kg_mapping = KG_Mapping(
                    id=str(uuid.uuid4()),
                    card_id=card_result.data['id'],
                    user_id=user_id,
                    nodes=[title, domain] + user_tags  # Simple node list
                )
                
                logger.info(f"Created KG mapping with {len(kg_mapping.nodes)} nodes")
                return 1
            else:
                logger.error(f"Failed to create flashcard: {card_result.error}")
                return 0

        except Exception as e:
            logger.error(f"Flashcard generation error: {e}")
            return 0

def create_web_server() -> WebServer:
    """Create and configure the web server"""
    return WebServer()

async def run_web_server(host: str = "127.0.0.1", port: int = 8001):
    """Run the web server"""
    server = create_web_server()

    logger.info(f"Starting web server at http://{host}:{port}")
    logger.info("Available endpoints:")
    logger.info(f"  - Main interface: http://{host}:{port}/")
    logger.info(f"  - API docs: http://{host}:{port}/docs")
    logger.info(f"  - Health check: http://{host}:{port}/api/health")

    config = uvicorn.Config(
        app=server.app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
    server_instance = uvicorn.Server(config)
    await server_instance.serve()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_web_server())