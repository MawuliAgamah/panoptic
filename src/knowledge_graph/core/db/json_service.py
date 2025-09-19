"""
JSON-based knowledge graph storage service.
Integrates the existing JsonKnowledgeStore with the knowledge graph client.
"""

import logging
from typing import Dict, List, Any, Optional
from services.knowledge_store import JsonKnowledgeStore

logger = logging.getLogger(__name__)

class JsonKnowledgeGraphService:
    """Service for storing knowledge graphs in JSON format."""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize JSON knowledge graph service.

        Args:
            config: Database configuration dictionary
        """
        self.config = config
        data_file = config.get('data_file') or config.get('db_location')

        # Initialize the JSON knowledge store
        self.knowledge_store = JsonKnowledgeStore(data_file=data_file)
        logger.info(f"JSON knowledge graph service initialized with file: {data_file}")

    def save_knowledge_graph(self, document_id: str, kg_data: Dict[str, Any], document_metadata: Dict[str, Any] = None) -> bool:
        """
        Save knowledge graph data to JSON store.

        Args:
            document_id: Document identifier
            kg_data: Knowledge graph data with entities and relationships
            document_metadata: Optional document metadata to attach to entities

        Returns:
            True if successful
        """
        try:
            return self.knowledge_store.save_knowledge_graph(document_id, kg_data, document_metadata)
        except Exception as e:
            logger.error(f"Failed to save knowledge graph for document {document_id}: {e}")
            return False

    def get_entities(self, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get entities from the knowledge store.

        Args:
            document_id: Optional document ID to filter by

        Returns:
            List of entities
        """
        entities = self.knowledge_store.get_entities()

        if document_id:
            # Filter entities by document ID
            filtered_entities = []
            for entity in entities:
                if document_id in entity.get('document_ids', []):
                    filtered_entities.append(entity)
            return filtered_entities

        return entities

    def get_relationships(self, document_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get relationships from the knowledge store.

        Args:
            document_id: Optional document ID to filter by

        Returns:
            List of relationships
        """
        relationships = self.knowledge_store.get_relationships()

        if document_id:
            # Filter relationships by document ID
            filtered_rels = []
            for rel in relationships:
                if document_id in rel.get('document_ids', []):
                    filtered_rels.append(rel)
            return filtered_rels

        return relationships

    def search_entities(self, query: str) -> List[Dict[str, Any]]:
        """Search entities by name or type."""
        return self.knowledge_store.search_entities(query)

    def search_relationships(self, query: str) -> List[Dict[str, Any]]:
        """Search relationships by entity names or relation types."""
        return self.knowledge_store.search_relationships(query)

    def get_entity_relationships(self, entity_name: str) -> List[Dict[str, Any]]:
        """Get all relationships for a specific entity."""
        return self.knowledge_store.get_entity_relationships(entity_name)

    def get_document_ontology(self, document_id: str) -> Dict[str, Any]:
        """
        Get complete ontology (entities + relationships) for a document.

        Args:
            document_id: Document identifier

        Returns:
            Dictionary with entities and relationships
        """
        entities = self.get_entities(document_id)
        relationships = self.get_relationships(document_id)

        return {
            'entities': entities,
            'relationships': relationships
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get knowledge store statistics."""
        return self.knowledge_store.get_stats()

    def query_knowledge_graph(self, query: str) -> Dict[str, Any]:
        """
        Query the knowledge graph using natural language.

        Args:
            query: Natural language query

        Returns:
            Query results with entities and relationships
        """
        # Simple implementation - search both entities and relationships
        entity_results = self.search_entities(query)
        relationship_results = self.search_relationships(query)

        return {
            'query': query,
            'entities': entity_results,
            'relationships': relationship_results,
            'total_results': len(entity_results) + len(relationship_results)
        }

    def close(self):
        """Close the service (no-op for JSON storage)."""
        logger.info("JSON knowledge graph service closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()