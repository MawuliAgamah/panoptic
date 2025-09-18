import os
from pathlib import Path
from knowledge_graph.core.db.sql_lite.repository import SqlLiteRepository

class SQLLiteService:
    """Service for SQLite database operations"""
    
    def __init__(self, db_path):
        self.repository = SqlLiteRepository(db_path)
        self.path = db_path
        
    def retrieve_document(self, document_id):
        """Get document by ID"""
        # Repository expects document_path not document_id
        return self.repository.retrieve_document(document_id)
    
    def delete_document(self, document_id):
        """Delete document by ID"""
        return self.repository.delete_document(document_id)
        
    def save_document(self, document):
        """Save document to database"""
        return self.repository.save_document(document)
    
    def get_chunks(self, document_id):
        """Get chunks for document"""
        # Query chunks from document_id
        data = self.repository.retrieve_document(document_id)
        if data and 'chunks' in data:
            return data['chunks']
        return []

    def save_entities_and_relationships(self, document_id, chunk_id, ontology):
        """Save entities and relationships extracted from ontology"""
        return self.repository.save_entities_and_relationships(document_id, chunk_id, ontology)
    
    def get_document_ontology(self, document_id):
        """Get all entities and relationships for a document"""
        return self.repository.get_document_ontology(document_id)
    
    def get_chunk_ontology(self, chunk_id):
        """Get all entities and relationships for a chunk"""
        return self.repository.get_chunk_ontology(chunk_id)
    
    def save_document_ontology(self, document_id, ontology):
        """Save full document ontology"""
        return self.repository.save_document_ontology(document_id, ontology)

    
