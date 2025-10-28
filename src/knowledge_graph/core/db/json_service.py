"""
JSON-based knowledge graph storage service.
Integrates the existing JsonKnowledgeStore with the knowledge graph client.
"""

import logging
from typing import Dict, List, Any, Optional
from collections import defaultdict
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

    def delete_document(self, document_id: str) -> bool:
        """Remove a document and its KG references from the JSON store."""
        try:
            return self.knowledge_store.delete_document(document_id)
        except Exception as exc:
            logger.error(f"Failed to delete document {document_id} from JSON store: {exc}")
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

    def get_all_domains(self) -> List[str]:
        """
        Get all unique domains from entity metadata.
        
        Returns:
            List of unique domain names
        """
        entities = self.get_entities()
        domains = set()
        
        for entity in entities:
            metadata = entity.get('metadata', {})
            # Check for domains in metadata
            if 'domains' in metadata:
                domains.update(metadata['domains'])
            # Check for categories in metadata
            if 'categories' in metadata:
                domains.update(metadata['categories'])
            # Check for tags in metadata
            if 'tags' in metadata:
                domains.update(metadata['tags'])
        
        return sorted(list(domains))
    
    def get_all_document_ids(self) -> List[str]:
        """
        Get all unique document IDs from entities.
        
        Returns:
            List of unique document IDs
        """
        entities = self.get_entities()
        document_ids = set()
        
        for entity in entities:
            document_ids.update(entity.get('document_ids', []))
        
        return sorted(list(document_ids))

    # --- Custom helpers for app-managed nodes/links ---
    def add_custom_entity(self, name: str, entity_type: str = "general", metadata: Optional[Dict[str, Any]] = None,
                          document_id: Optional[str] = None) -> Dict[str, Any]:
        """Add an entity with custom metadata (used for user-created nodes)."""
        return self.knowledge_store.add_entity(name=name, entity_type=entity_type, document_id=document_id, metadata=metadata or {})

    def add_custom_relationship(self, source_name: str, relation_type: str, target_name: str,
                                document_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Add a relationship by entity names (new format)."""
        return self.knowledge_store.add_relationship(source_entity=source_name, relation_type=relation_type,
                                                     target_entity=target_name, document_id=document_id, metadata=metadata or {})

    def get_entity_by_id(self, entity_id: int) -> Optional[Dict[str, Any]]:
        for e in self.knowledge_store.get_entities():
            if e.get('id') == entity_id:
                return e
        return None

    def get_entity_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        for e in self.knowledge_store.get_entities():
            if e.get('name', '').lower() == name.lower():
                return e
        return None

    def add_entities_batch(self, entities_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add multiple entities in batch and return the created entities.
        
        Args:
            entities_data: List of entity dictionaries
            
        Returns:
            List of created entity objects with IDs
        """
        created_entities = []
        for entity_data in entities_data:
            try:
                entity = self.add_custom_entity(
                    name=entity_data.get('name'),
                    entity_type=entity_data.get('type', 'extracted'),
                    metadata=entity_data.get('metadata', {}),
                    document_id=entity_data.get('document_id')
                )
                created_entities.append(entity)
                logger.debug(f"Added entity: {entity['name']} (ID: {entity['id']})")
            except Exception as e:
                logger.warning(f"Failed to add entity {entity_data.get('name')}: {e}")
        
        return created_entities

    def add_relationships_batch(self, relationships_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Add multiple relationships in batch and return the created relationships.
        
        Args:
            relationships_data: List of relationship dictionaries
            
        Returns:
            List of created relationship objects with IDs
        """
        created_relationships = []
        for rel_data in relationships_data:
            try:
                relationship = self.add_custom_relationship(
                    source_name=rel_data.get('source_entity') or rel_data.get('source'),
                    relation_type=rel_data.get('relation_type') or rel_data.get('type'),
                    target_name=rel_data.get('target_entity') or rel_data.get('target'),
                    document_id=rel_data.get('document_id'),
                    metadata=rel_data.get('metadata', {})
                )
                created_relationships.append(relationship)
                logger.debug(f"Added relationship: {relationship.get('source_entity')} -> {relationship.get('target_entity')}")
            except Exception as e:
                logger.warning(f"Failed to add relationship {rel_data}: {e}")
        
        return created_relationships

    def clear_knowledge_store(self) -> Dict[str, Any]:
        """
        Clear all entities and relationships from the knowledge store.
        
        Returns:
            Dictionary with counts of cleared items
        """
        try:
            # Get current counts before clearing
            entities_before = len(self.get_entities())
            relationships_before = len(self.get_relationships())
            
            # Clear the knowledge store
            self.knowledge_store.clear_all_data()
            
            # Get counts after clearing
            entities_after = len(self.get_entities())
            relationships_after = len(self.get_relationships())
            
            result = {
                'entities_cleared': entities_before - entities_after,
                'relationships_cleared': relationships_before - relationships_after,
                'entities_remaining': entities_after,
                'relationships_remaining': relationships_after,
                'success': True
            }
            
            logger.info(f"Knowledge store cleared: {result['entities_cleared']} entities, {result['relationships_cleared']} relationships")
            return result
            
        except Exception as e:
            logger.error(f"Failed to clear knowledge store: {e}")
            return {
                'entities_cleared': 0,
                'relationships_cleared': 0,
                'entities_remaining': len(self.get_entities()),
                'relationships_remaining': len(self.get_relationships()),
                'success': False,
                'error': str(e)
            }
    
    def get_domains_by_document(self) -> Dict[str, List[str]]:
        """
        Get domains organized by document ID.
        
        Returns:
            Dictionary mapping document IDs to lists of domains
        """
        entities = self.get_entities()
        doc_domains = defaultdict(set)
        
        for entity in entities:
            doc_ids = entity.get('document_ids', [])
            metadata = entity.get('metadata', {})
            
            # Collect domains from metadata
            domains = set()
            if 'domains' in metadata:
                domains.update(metadata['domains'])
            if 'categories' in metadata:
                domains.update(metadata['categories'])
            if 'tags' in metadata:
                domains.update(metadata['tags'])
            
            # Add domains to each document
            for doc_id in doc_ids:
                doc_domains[doc_id].update(domains)
        
        # Convert sets to sorted lists
        return {doc_id: sorted(list(domains)) for doc_id, domains in doc_domains.items()}

    def close(self):
        """Close the service (no-op for JSON storage)."""
        logger.info("JSON knowledge graph service closed")

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
