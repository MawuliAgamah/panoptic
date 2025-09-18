import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, Neo4jError

logger = logging.getLogger(__name__)

class Neo4jService:
    """Service for Neo4j database operations to store knowledge graphs"""

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize Neo4j service

        Args:
            config: Dictionary with neo4j connection details
                   Required keys: host, port, username, password, database
        """
        self.config = config
        self.driver = None
        self._connect()

    def _connect(self):
        """Establish connection to Neo4j database"""
        try:
            uri = f"bolt://{self.config['host']}:{self.config['port']}"
            self.driver = GraphDatabase.driver(
                uri,
                auth=(self.config['username'], self.config['password']),
                database=self.config.get('database', 'neo4j')
            )

            # Test connection
            with self.driver.session() as session:
                session.run("RETURN 1")

            logger.info(f"Connected to Neo4j at {uri}")

        except ServiceUnavailable as e:
            logger.error(f"Failed to connect to Neo4j: {e}")
            raise
        except Exception as e:
            logger.error(f"Neo4j connection error: {e}")
            raise

    def save_knowledge_graph(self, document_id: str, kg_graph: Dict[str, Any]) -> bool:
        """
        Save kg-gen output to Neo4j as document knowledge graph

        Args:
            document_id: Unique document identifier
            kg_graph: kg-gen output format with 'entities' and 'relations'

        Returns:
            bool: True if successful
        """
        try:
            with self.driver.session() as session:
                # Start transaction for atomicity
                with session.begin_transaction() as tx:

                    # Create document node
                    tx.run(
                        """
                        MERGE (d:Document {id: $document_id})
                        SET d.last_updated = datetime()
                        """,
                        document_id=document_id
                    )

                    # Create entity nodes and connect to document
                    entities = kg_graph.get('entities', set())
                    for entity in entities:
                        tx.run(
                            """
                            MERGE (e:Entity {name: $entity_name})
                            SET e.last_updated = datetime()
                            WITH e
                            MATCH (d:Document {id: $document_id})
                            MERGE (d)-[:CONTAINS]->(e)
                            """,
                            entity_name=entity,
                            document_id=document_id
                        )

                    # Create relationships between entities
                    relations = kg_graph.get('relations', set())
                    for relation_tuple in relations:
                        if len(relation_tuple) >= 3:
                            source, relation_type, target = relation_tuple[0], relation_tuple[1], relation_tuple[2]

                            # Clean relation type for Neo4j (no spaces, special chars)
                            clean_relation = self._clean_relation_type(relation_type)

                            tx.run(
                                f"""
                                MATCH (s:Entity {{name: $source_name}})
                                MATCH (t:Entity {{name: $target_name}})
                                MERGE (s)-[r:{clean_relation}]->(t)
                                SET r.original_relation = $original_relation,
                                    r.document_id = $document_id,
                                    r.last_updated = datetime()
                                """,
                                source_name=source,
                                target_name=target,
                                original_relation=relation_type,
                                document_id=document_id
                            )

                    logger.info(f"Saved knowledge graph for document {document_id}: {len(entities)} entities, {len(relations)} relations")
                    return True

        except Neo4jError as e:
            logger.error(f"Neo4j error saving knowledge graph: {e}")
            return False
        except Exception as e:
            logger.error(f"Error saving knowledge graph: {e}")
            return False

    def _clean_relation_type(self, relation: str) -> str:
        """Clean relation type for use as Neo4j relationship type"""
        import re
        # Replace spaces and special chars with underscores, convert to uppercase
        cleaned = re.sub(r'[^a-zA-Z0-9_]', '_', relation)
        cleaned = cleaned.upper().strip('_')
        return cleaned or "RELATED_TO"

    def get_document_entities(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all entities for a document"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (d:Document {id: $document_id})-[:CONTAINS]->(e:Entity)
                    RETURN e.name as entity_name
                    ORDER BY e.name
                    """,
                    document_id=document_id
                )

                entities = [{"name": record["entity_name"]} for record in result]
                logger.debug(f"Retrieved {len(entities)} entities for document {document_id}")
                return entities

        except Neo4jError as e:
            logger.error(f"Neo4j error getting entities: {e}")
            return []

    def get_document_relationships(self, document_id: str) -> List[Dict[str, Any]]:
        """Get all relationships for a document"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (s:Entity)-[r]->(t:Entity)
                    WHERE r.document_id = $document_id
                    RETURN s.name as source, type(r) as relation_type,
                           r.original_relation as original_relation, t.name as target
                    ORDER BY s.name, t.name
                    """,
                    document_id=document_id
                )

                relationships = []
                for record in result:
                    relationships.append({
                        "source": record["source"],
                        "target": record["target"],
                        "relation_type": record["relation_type"],
                        "original_relation": record["original_relation"]
                    })

                logger.debug(f"Retrieved {len(relationships)} relationships for document {document_id}")
                return relationships

        except Neo4jError as e:
            logger.error(f"Neo4j error getting relationships: {e}")
            return []

    def search_entities(self, search_term: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for entities by name"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    """
                    MATCH (e:Entity)
                    WHERE toLower(e.name) CONTAINS toLower($search_term)
                    RETURN e.name as entity_name,
                           [(e)<-[:CONTAINS]-(d:Document) | d.id] as documents
                    ORDER BY e.name
                    LIMIT $limit
                    """,
                    search_term=search_term,
                    limit=limit
                )

                entities = []
                for record in result:
                    entities.append({
                        "name": record["entity_name"],
                        "documents": record["documents"]
                    })

                return entities

        except Neo4jError as e:
            logger.error(f"Neo4j error searching entities: {e}")
            return []

    def get_entity_connections(self, entity_name: str, depth: int = 1) -> List[Dict[str, Any]]:
        """Get connected entities for a given entity"""
        try:
            with self.driver.session() as session:
                result = session.run(
                    f"""
                    MATCH path = (e:Entity {{name: $entity_name}})-[*1..{depth}]-(connected:Entity)
                    RETURN DISTINCT connected.name as connected_entity,
                           length(path) as distance
                    ORDER BY distance, connected_entity
                    LIMIT 20
                    """,
                    entity_name=entity_name
                )

                connections = []
                for record in result:
                    connections.append({
                        "entity": record["connected_entity"],
                        "distance": record["distance"]
                    })

                return connections

        except Neo4jError as e:
            logger.error(f"Neo4j error getting connections: {e}")
            return []

    def delete_document_graph(self, document_id: str) -> bool:
        """Delete all knowledge graph data for a document"""
        try:
            with self.driver.session() as session:
                with session.begin_transaction() as tx:

                    # Delete document's relationships
                    tx.run(
                        "MATCH ()-[r {document_id: $document_id}]-() DELETE r",
                        document_id=document_id
                    )

                    # Delete entities that are only connected to this document
                    tx.run(
                        """
                        MATCH (d:Document {id: $document_id})-[:CONTAINS]->(e:Entity)
                        WHERE NOT exists((:Document)-[:CONTAINS]->(e)) OR
                              all(doc IN [(:Document)-[:CONTAINS]->(e)] WHERE doc.id = $document_id)
                        DETACH DELETE e
                        """,
                        document_id=document_id
                    )

                    # Delete document node
                    tx.run(
                        "MATCH (d:Document {id: $document_id}) DELETE d",
                        document_id=document_id
                    )

                    logger.info(f"Deleted knowledge graph for document {document_id}")
                    return True

        except Neo4jError as e:
            logger.error(f"Neo4j error deleting document graph: {e}")
            return False

    def get_graph_statistics(self) -> Dict[str, int]:
        """Get basic statistics about the knowledge graph"""
        try:
            with self.driver.session() as session:
                # Count entities
                entity_count = session.run("MATCH (e:Entity) RETURN count(e) as count").single()["count"]

                # Count documents
                doc_count = session.run("MATCH (d:Document) RETURN count(d) as count").single()["count"]

                # Count relationships
                rel_count = session.run("MATCH ()-[r]->() RETURN count(r) as count").single()["count"]

                return {
                    "entities": entity_count,
                    "documents": doc_count,
                    "relationships": rel_count
                }

        except Neo4jError as e:
            logger.error(f"Neo4j error getting statistics: {e}")
            return {"entities": 0, "documents": 0, "relationships": 0}

    def test_connection(self) -> bool:
        """Test if Neo4j connection is working"""
        try:
            with self.driver.session() as session:
                result = session.run("RETURN 'Connection OK' as status")
                status = result.single()["status"]
                logger.info(f"Neo4j connection test: {status}")
                return True

        except Exception as e:
            logger.error(f"Neo4j connection test failed: {e}")
            return False

    def close(self):
        """Close Neo4j driver connection"""
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()