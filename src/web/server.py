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

from knowledge_graph import create_json_client
from flashcards import create_flashcard_service
from flashcards.models.knowledge_graph import (
    KGMapping, KGEntity, KGTopic, KGDocument,
    create_simple_entity_mapping, create_topic_mapping, create_document_mapping
)

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
        self.flashcard_service = None
        self.setup_routes()
        self.setup_static_files()

    def setup_static_files(self):
        """Setup static file serving for the visualization"""
        # Get the vis directory path
        current_dir = Path(__file__).parent
        vis_dir = current_dir.parent / "vis"

        if vis_dir.exists():
            # Mount vis directory as static files
            self.app.mount("/vis", StaticFiles(directory=str(vis_dir)), name="vis")
            logger.info(f"Mounted vis directory: {vis_dir}")
        else:
            logger.warning(f"Vis directory not found: {vis_dir}")

    def setup_routes(self):
        """Setup all API routes"""

        @self.app.get("/", response_class=HTMLResponse)
        async def root():
            """Serve the main visualization page"""
            current_dir = Path(__file__).parent
            vis_dir = current_dir.parent / "vis"
            index_path = vis_dir / "index.html"

            if index_path.exists():
                return FileResponse(str(index_path))
            else:
                return HTMLResponse("""
                <html>
                    <body>
                        <h1>Knowledge Graph Visualization</h1>
                        <p>Visualization files not found. Please check the vis/ directory.</p>
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

        @self.app.get("/database/knowledge_store.json")
        async def get_knowledge_graph_data():
            """Serve the knowledge graph data for visualization"""
            try:
                # Get the database path
                current_dir = Path(__file__).parent
                project_root = current_dir.parent.parent
                kg_file = project_root / "database" / "knowledge_store.json"

                if kg_file.exists():
                    with open(kg_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    return JSONResponse(content=data)
                else:
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
                    return JSONResponse(content=sample_data)

            except Exception as e:
                logger.error(f"Error serving knowledge graph data: {e}")
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
            generate_flashcards: bool = Form(False)
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

                    if auto_extract:
                        entities_extracted, relationships_created = await self.process_document_kg(
                            str(temp_file), title, type, domain, description, user_tags
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
                if not self.flashcard_service:
                    self.flashcard_service = create_flashcard_service(enable_anki=False)

                # Get overall stats (you might need to implement this in your service)
                total_cards = 0
                total_decks = 0

                return JSONResponse(content={
                    "total_cards": total_cards,
                    "total_decks": total_decks,
                    "algorithms_available": list(self.flashcard_service.get_available_algorithms().keys())
                })

            except Exception as e:
                logger.error(f"Error getting flashcard stats: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    async def process_document_kg(self, file_path: str, title: str, doc_type: str,
                                 domain: str, description: str, user_tags: List[str]) -> tuple[int, int]:
        """Process document through knowledge graph extraction"""
        try:
            logger.info(f"Processing document through KG pipeline: {title}")

            # Generate document ID
            doc_id = f"uploaded_{title.replace(' ', '_').replace('.', '_').lower()}_{uuid.uuid4().hex[:8]}"

            # Initialize JSON client
            with create_json_client() as client:
                # Add document to KG system
                document_id = client.add_document(
                    document_path=file_path,
                    document_id=doc_id,
                    document_type=doc_type
                )

                # Extract ontology if auto-extract is enabled
                client.extract_document_ontology(document_id)

                # Get statistics
                stats = client.get_knowledge_graph_stats()
                entities_extracted = stats.get('total_entities', 0)
                relationships_created = stats.get('total_relationships', 0)

                logger.info(f"KG processing complete: {entities_extracted} entities, {relationships_created} relationships")
                return entities_extracted, relationships_created

        except Exception as e:
            logger.error(f"KG processing error: {e}")
            return 0, 0

    async def generate_flashcards_from_document(self, file_path: str, title: str,
                                              domain: str, user_tags: List[str]) -> int:
        """Generate flashcards from uploaded document"""
        try:
            logger.info(f"Generating flashcards from document: {title}")

            if not self.flashcard_service:
                self.flashcard_service = create_flashcard_service(enable_anki=False)

            # For now, create a sample flashcard with KG mapping
            # In a real implementation, you'd extract content and create multiple cards

            # Create KG entities and topics from user input
            entities = []
            topics = []

            # Create entity for the document itself
            doc_entity = KGEntity(
                entity_id=str(uuid.uuid4()),
                name=title,
                entity_type="document",
                confidence=1.0
            )
            entities.append(doc_entity)

            # Create topic for the domain
            domain_topic = KGTopic(
                topic_id=str(uuid.uuid4()),
                name=domain,
                category="domain",
                confidence=1.0
            )
            topics.append(domain_topic)

            # Create entities from user tags
            for tag in user_tags:
                tag_entity = KGEntity(
                    entity_id=str(uuid.uuid4()),
                    name=tag,
                    entity_type="concept",
                    confidence=0.8
                )
                entities.append(tag_entity)

            # Create KG document reference
            kg_document = KGDocument(
                document_id=str(uuid.uuid4()),
                title=title,
                document_type="uploaded",
                file_path=file_path
            )

            # Create KG mapping
            kg_mapping = KGMapping.create_new(
                primary_entities=entities,
                primary_topics=topics,
                source_document=kg_document,
                extraction_method="user_uploaded"
            )

            # Create a sample flashcard with KG mapping
            # TODO: Replace with actual content extraction
            user_id = "web_user"  # You might want to implement user sessions

            # Create or get default deck
            deck = self.flashcard_service.create_deck(
                user_id=user_id,
                name=f"{domain.title()} - {title}",
                description=f"Flashcards from uploaded document: {title}"
            )

            if deck:
                # Create a sample flashcard
                card = self.flashcard_service.create_card(
                    deck_id=deck.deck_id,
                    user_id=user_id,
                    front=f"What is the main topic of '{title}'?",
                    back=f"This document covers {domain} and includes concepts like: {', '.join(user_tags)}",
                    tags=[domain] + user_tags,
                    kg_mapping=kg_mapping
                )

                if card:
                    logger.info(f"Created flashcard with KG mapping for: {title}")
                    return 1

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