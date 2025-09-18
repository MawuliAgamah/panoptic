import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from rich.console import Console
import json
import uuid
console = Console()
from .queries import (
    CREATE_DOCUMENT_TABLE,
    CREATE_CHUNK_TABLE,
    CREATE_ENTITY_TABLE,
    CREATE_RELATIONSHIP_TABLE,
    CREATE_DOCUMENT_ONTOLOGY_TABLE,
    SAVE_DOCUMENT,
    SAVE_CHUNK,
    SAVE_ENTITY,
    SAVE_RELATIONSHIP,
    SAVE_DOCUMENT_ONTOLOGY,
    DOCUMENT_EXISTS_QUERY,
    GET_DOCUMENT_DATA,
    GET_CHUNK_DATA,
    GET_ENTITIES_BY_DOCUMENT,
    GET_RELATIONSHIPS_BY_DOCUMENT,
    GET_ENTITIES_BY_CHUNK,
    GET_RELATIONSHIPS_BY_CHUNK
)


class SqlLiteRepository:
    """Handles SQL operations for documents and chunks"""

    def __init__(self, db_path=None):
        # Set default path in project's data directory
        if db_path is None:
            project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
            db_path = project_root / "data" / "document_db.db"
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = str(db_path)
        console.print(f"[bold blue]Using database at: {self.db_path}[/bold blue]")
        self._initialize_database()

    def _initialize_database(self):
        """Initialize database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(CREATE_DOCUMENT_TABLE)
                cursor.execute(CREATE_CHUNK_TABLE)
                cursor.execute(CREATE_ENTITY_TABLE)
                cursor.execute(CREATE_RELATIONSHIP_TABLE)
                cursor.execute(CREATE_DOCUMENT_ONTOLOGY_TABLE)
                conn.commit()
                console.print("[bold green]✓[/bold green] Database initialized successfully")
        except Exception as e:
            console.print(f"[red]Error initializing database: {e}[/red]")
            raise

    def doc_exists(self, document_id: str) -> bool:  
        """Check if the document exists"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Try document_id first
                cursor.execute(DOCUMENT_EXISTS_QUERY, (document_id,))  
                result = cursor.fetchone()
                
                # If not found, try file_path as fallback
                if result is None:
                    cursor.execute("SELECT * FROM documents WHERE file_path = ?", (document_id,))
                    result = cursor.fetchone()
                    
                return result is not None
        except Exception as e:
            console.print(f"[red]Error checking if document exists: {e}[/red]")
            return False

    def save_document(self, document: Any) -> bool:
        """Save document and its chunks to the database"""
        try:
            timestamp = datetime.now()
            
            # Debug information
            self._print_debug_info(document, timestamp)
            console.print(f"[yellow]Attempting to save document: {document.file_path}[/yellow]")
            console.print(f"[blue]Using database at: {self.db_path}[/blue]")

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                try:
                    # Start transaction
                    cursor.execute("BEGIN TRANSACTION")
                    console.print("[yellow]Started database transaction[/yellow]")
                    
                    # Save document and get its ID
                    doc_values = (
                        document.id,
                        document.file_path,
                        document.hash if hasattr(document, 'hash') else None,
                        document.file_type,
                        document.title,
                        document.metadata.summary if hasattr(document.metadata, 'summary') else None,
                        document.raw_content,
                        document.clean_content,
                        timestamp,
                        timestamp,
                        timestamp
                    )
                    
                    console.print(f"[yellow]Saving document with values: {doc_values}[/yellow]")
                    cursor.execute(SAVE_DOCUMENT, doc_values)
                    document_id = cursor.fetchone()[0]  # Get the returned ID
                    console.print(f"[green]Saved document with ID: {document_id}[/green]")
                    
                    # Delete existing chunks for this document
                    cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
                    console.print(f"[yellow]Deleted existing chunks for document {document_id}[/yellow]")
                    
                    # Save chunks
                    chunk_ids = []  # Store chunk IDs for linking
                    if hasattr(document, 'textChunks') and document.textChunks:
                        console.print(f"[yellow]Saving {len(document.textChunks)} chunks[/yellow]")
                        for i, chunk in enumerate(document.textChunks):
                            chunk_values = (
                                document_id,
                                chunk.content,
                                i,  # chunk_index
                                chunk.metadata.word_count,
                                chunk.metadata.token_count if hasattr(chunk.metadata, 'token_count') else None,
                                chunk.metadata.language,
                                json.dumps(chunk.metadata.topics) if chunk.metadata.topics else None,
                                json.dumps(chunk.metadata.keywords) if chunk.metadata.keywords else None,
                                chunk.metadata.start_index,
                                chunk.metadata.end_index,
                                None,  # previous_chunk_id - will be updated
                                None   # next_chunk_id - will be updated
                            )
                            console.print(f"[yellow]Saving chunk {i} with values: {chunk_values}[/yellow]")
                            cursor.execute(SAVE_CHUNK, chunk_values)
                            chunk_ids.append(cursor.lastrowid)
                            console.print(f"[green]Saved chunk with ID: {cursor.lastrowid}[/green]")
                    else:
                        console.print("[red]No chunks found in document[/red]")
                    
                    # Update chunk links
                    if len(chunk_ids) > 1:
                        console.print("[yellow]Updating chunk links[/yellow]")
                        for i, chunk_id in enumerate(chunk_ids):
                            prev_id = chunk_ids[i-1] if i > 0 else None
                            next_id = chunk_ids[i+1] if i < len(chunk_ids)-1 else None
                            
                            cursor.execute("""
                                UPDATE chunks 
                                SET previous_chunk_id = ?, next_chunk_id = ?
                                WHERE id = ?
                            """, (prev_id, next_id, chunk_id))
                    
                    # Commit transaction
                    conn.commit()
                    console.print("[bold green]✓[/bold green] Document and chunks saved successfully")
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    console.print(f"[red]Error during save, rolling back: {e}[/red]")
                    raise e
                
        except sqlite3.Error as e:
            console.print(f"[red]SQLite error: {str(e)}[/red]")
            raise
        except Exception as e:
            console.print(f"[red]Unexpected error: {str(e)}[/red]")
            raise

    def retrieve_document(self, document_id: str) -> Optional[Dict]:
        """Get document and its chunks from the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if we're using the new schema with document_id
                cursor.execute("PRAGMA table_info(documents)")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                
                # Determine which column to use for lookup
                if 'document_id' in column_names:
                    # Use document_id field
                    cursor.execute(GET_DOCUMENT_DATA, (document_id,))
                    document_data = cursor.fetchall()
                    cursor.execute(GET_CHUNK_DATA, (document_id,))
                    chunk_data = cursor.fetchall()
                else:
                    # Fall back to using file_path for older schema
                    console.print("[yellow]Warning: Using legacy schema without document_id column[/yellow]")
                    cursor.execute("SELECT * FROM documents WHERE file_path = ?", (document_id,))
                    document_data = cursor.fetchall()
                    if document_data:
                        cursor.execute("SELECT * FROM chunks WHERE document_id = ?", (document_data[0][0],))
                        chunk_data = cursor.fetchall()
                    else:
                        chunk_data = []
                
                data = {'document': document_data, 'chunks': chunk_data}
                return data
                
        except Exception as e:
            console.print(f"[red]Error retrieving document: {e}[/red]")
            return None
        
    def delete_document(self, document_id: str) -> bool:
        """Delete document by ID"""
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
                
            # Start transaction
            cursor.execute("BEGIN TRANSACTION")
                
            # Delete associated chunks first (using ON DELETE CASCADE would make this unnecessary,
            # but we'll explicitly delete them first to be safe)
            cursor.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
            console.print(f"[yellow]Deleted associated chunks for document {document_id}[/yellow]")
                
            # Then delete the document
            cursor.execute("DELETE FROM documents WHERE document_id = ?", (document_id,))
                
            # Commit changes
            conn.commit()
            console.print(f"[bold green]✓[/bold green] Document and all associated chunks deleted with ID: {document_id}")
            return True
                
        except Exception as e:
            # Rollback on error
            if conn:
                conn.rollback()
            console.print(f"[red]Error deleting document: {e}[/red]")
            return False
        finally:
            # Close connection if it was opened
            if conn:
                conn.close()

    def save_document_ontology(self, document_id: str, ontology: Any) -> bool:
        """Save ontology to document"""
        try:
            # Serialize ontology to JSON if needed
            ontology_json = json.dumps(ontology) if isinstance(ontology, dict) else json.dumps(ontology.dict())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(SAVE_DOCUMENT_ONTOLOGY, (document_id, ontology_json))
                conn.commit()
                console.print(f"[green]Saved ontology for document: {document_id}[/green]")
                return True
        except Exception as e:
            console.print(f"[red]Error saving document ontology: {e}[/red]")
            return False
                
    def save_entities_and_relationships(self, document_id: str, chunk_id: Optional[int], ontology: Any) -> bool:
        """Save entities and relationships extracted from ontology"""
        try:
            console.print(f"[yellow]Saving ontology for document: {document_id}[/yellow]")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                try:
                    # Start transaction
                    cursor.execute("BEGIN TRANSACTION")
                    console.print("[yellow]Started ontology transaction[/yellow]")
                    
                    # Process entities
                    entity_ids = {}  # Map entity names to IDs for relationship creation
                    
                    if hasattr(ontology, 'entities'):
                        entities = ontology.entities
                    elif isinstance(ontology, dict) and 'entities' in ontology:
                        entities = ontology['entities']
                    else:
                        entities = []
                    
                    console.print(f"[yellow]Processing {len(entities)} entities[/yellow]")
                    
                    for entity in entities:
                        # Extract entity data
                        if hasattr(entity, 'name'):
                            name = entity.name
                            entity_type = entity.type
                            category = entity.category
                        else:
                            name = entity['name']
                            entity_type = entity['type']
                            category = entity['category']
                        
                        # Generate unique ID for entity
                        entity_id = str(uuid.uuid4())
                        entity_ids[name] = entity_id
                        
                        # Save entity
                        cursor.execute(SAVE_ENTITY, (
                            entity_id,
                            name,
                            entity_type,
                            category,
                            document_id,
                            chunk_id
                        ))
                        console.print(f"[green]Saved entity: {name} ({entity_type}/{category})[/green]")
                    
                    # Process relationships
                    relationships = []
                    
                    if isinstance(ontology, dict):
                        if 'relationships' in ontology:
                            relationships = ontology['relationships']
                    elif hasattr(ontology, 'relationships'):
                        relationships = ontology.relationships
                    
                    console.print(f"[yellow]Processing {len(relationships)} relationships[/yellow]")
                    
                    for relationship in relationships:
                        # Extract relationship data
                        if hasattr(relationship, 'source'):
                            source = relationship.source
                            target = relationship.target
                            relation = relationship.relation
                            context = relationship.context
                        else:
                            source = relationship['source']
                            target = relationship['target']
                            relation = relationship['relation']
                            context = relationship['context']
                        
                        # Get entity IDs
                        source_entity_id = entity_ids.get(source)
                        target_entity_id = entity_ids.get(target)
                        
                        # Skip if either entity doesn't exist
                        if not source_entity_id or not target_entity_id:
                            console.print(f"[red]Skipping relationship: {source} → {relation} → {target} (missing entity)[/red]")
                            continue
                        
                        # Generate unique ID for relationship
                        relationship_id = str(uuid.uuid4())
                        
                        # Save relationship
                        cursor.execute(SAVE_RELATIONSHIP, (
                            relationship_id,
                            source_entity_id,
                            target_entity_id,
                            relation,
                            context,
                            document_id,
                            chunk_id
                        ))
                        console.print(f"[green]Saved relationship: {source} → {relation} → {target}[/green]")
                    
                    # Commit transaction
                    conn.commit()
                    console.print("[bold green]✓[/bold green] Ontology saved successfully")
                    return True
                    
                except Exception as e:
                    # Rollback on error
                    conn.rollback()
                    console.print(f"[red]Error saving ontology: {e}[/red]")
                    return False
                
        except Exception as e:
            console.print(f"[red]Error connecting to database: {e}[/red]")
            return False

    def get_document_ontology(self, document_id: str) -> Dict:
        """Get all entities and relationships for a document"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get entities
                cursor.execute(GET_ENTITIES_BY_DOCUMENT, (document_id,))
                entity_rows = cursor.fetchall()
                
                # Get relationships with entity details
                cursor.execute(GET_RELATIONSHIPS_BY_DOCUMENT, (document_id,))
                relationship_rows = cursor.fetchall()
                
                # Format response
                entities = []
                for row in entity_rows:
                    entity = {
                        'entity_id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'category': row[3],
                        'document_id': row[4],
                        'chunk_id': row[5],
                        'created_at': row[6]
                    }
                    entities.append(entity)
                
                relationships = []
                for row in relationship_rows:
                    relationship = {
                        'relationship_id': row[0],
                        'source_entity_id': row[1],
                        'target_entity_id': row[2],
                        'relation': row[3],
                        'context': row[4],
                        'document_id': row[5],
                        'chunk_id': row[6],
                        'created_at': row[7],
                        'source_name': row[8],
                        'source_type': row[9],
                        'source_category': row[10],
                        'target_name': row[11],
                        'target_type': row[12],
                        'target_category': row[13]
                    }
                    relationships.append(relationship)
                
                return {
                    'entities': entities,
                    'relationships': relationships
                }
                
        except Exception as e:
            console.print(f"[red]Error retrieving ontology: {e}[/red]")
            return {'entities': [], 'relationships': []}

    def get_chunk_ontology(self, chunk_id: int) -> Dict:
        """Get all entities and relationships for a chunk"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get entities
                cursor.execute(GET_ENTITIES_BY_CHUNK, (chunk_id,))
                entity_rows = cursor.fetchall()
                
                # Get relationships with entity details
                cursor.execute(GET_RELATIONSHIPS_BY_CHUNK, (chunk_id,))
                relationship_rows = cursor.fetchall()
                
                # Format response
                entities = []
                for row in entity_rows:
                    entity = {
                        'entity_id': row[0],
                        'name': row[1],
                        'type': row[2],
                        'category': row[3],
                        'document_id': row[4],
                        'chunk_id': row[5],
                        'created_at': row[6]
                    }
                    entities.append(entity)
                
                relationships = []
                for row in relationship_rows:
                    relationship = {
                        'relationship_id': row[0],
                        'source_entity_id': row[1],
                        'target_entity_id': row[2],
                        'relation': row[3],
                        'context': row[4],
                        'document_id': row[5],
                        'chunk_id': row[6],
                        'created_at': row[7],
                        'source_name': row[8],
                        'source_type': row[9],
                        'source_category': row[10],
                        'target_name': row[11],
                        'target_type': row[12],
                        'target_category': row[13]
                    }
                    relationships.append(relationship)
                
                return {
                    'entities': entities,
                    'relationships': relationships
                }
                
        except Exception as e:
            console.print(f"[red]Error retrieving chunk ontology: {e}[/red]")
            return {'entities': [], 'relationships': []}

    def _print_debug_info(self, document: Any, timestamp: datetime) -> None:
        """Print debug information about the document"""
        from rich.table import Table
        
        table = Table(title="--Debug - Saving Document", show_header=True)
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Type", style="green")
        
        # Document info
        table.add_row("Path", repr(document.file_path), str(type(document.file_path)))
        table.add_row("Type", repr(document.file_type), str(type(document.file_type)))
        table.add_row("Title", repr(document.title), str(type(document.title)))
        table.add_row("Chunks", str(len(document.textChunks)), str(type(document.textChunks)))
        
        # Timestamps
        table.add_row("Created At", str(timestamp), str(type(timestamp)))
        table.add_row("Updated At", str(timestamp), str(type(timestamp)))
        table.add_row("Last Modified", str(timestamp), str(type(timestamp)))
        
        console.print()
        console.print(table)
        console.print()

    def query(self, query: str, params: Optional[tuple] = None) -> List[tuple]:
        """Execute a custom query"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                if params:
                    cursor.execute(query, params)
                else:
                    cursor.execute(query)
                results = cursor.fetchall()
                return results
        except Exception as e:
            console.print(f"[red]Error executing query: {e}[/red]")
            raise