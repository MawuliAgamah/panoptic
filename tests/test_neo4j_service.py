import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.core.db.neo4j.service import Neo4jService

class TestNeo4jService:
    """Test Neo4j service implementation"""

    def setup_method(self):
        """Setup test environment with mock Neo4j driver"""
        self.config = {
            'host': 'localhost',
            'port': 7687,
            'username': 'neo4j',
            'password': 'password',
            'database': 'test_db'
        }

        # Mock the Neo4j driver
        self.mock_driver = MagicMock()
        self.mock_session = MagicMock()
        self.mock_transaction = MagicMock()
        self.mock_driver.session.return_value = self.mock_session
        self.mock_session.begin_transaction.return_value = self.mock_transaction

        # Mock the session as context manager
        self.mock_session.__enter__ = Mock(return_value=self.mock_session)
        self.mock_session.__exit__ = Mock(return_value=None)

        # Mock the transaction as context manager
        self.mock_transaction.__enter__ = Mock(return_value=self.mock_transaction)
        self.mock_transaction.__exit__ = Mock(return_value=None)

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_initialization_success(self, mock_graph_driver):
        """Test successful Neo4j service initialization"""
        mock_graph_driver.return_value = self.mock_driver

        service = Neo4jService(self.config)

        assert service.config == self.config
        assert service.driver == self.mock_driver
        mock_graph_driver.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password"),
            database="test_db"
        )

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_initialization_failure(self, mock_graph_driver):
        """Test Neo4j service initialization failure"""
        from neo4j.exceptions import ServiceUnavailable
        mock_graph_driver.side_effect = ServiceUnavailable("Connection failed")

        with pytest.raises(ServiceUnavailable):
            Neo4jService(self.config)

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_save_knowledge_graph_success(self, mock_graph_driver):
        """Test successful knowledge graph saving"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Test data
        document_id = "doc_123"
        kg_graph = {
            'entities': {'Python', 'Machine Learning', 'Data Science'},
            'relations': [
                ('Python', 'used_for', 'Machine Learning'),
                ('Machine Learning', 'part_of', 'Data Science')
            ]
        }

        result = service.save_knowledge_graph(document_id, kg_graph)

        assert result == True
        assert self.mock_driver.session.called
        assert self.mock_transaction.run.call_count == 6  # 1 document + 3 entities + 2 relations

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_save_knowledge_graph_with_invalid_relations(self, mock_graph_driver):
        """Test handling of invalid relation tuples"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Test data with invalid relation (less than 3 elements)
        document_id = "doc_123"
        kg_graph = {
            'entities': {'Python'},
            'relations': [('Python',), ('Source', 'Target')]  # Invalid tuples
        }

        result = service.save_knowledge_graph(document_id, kg_graph)

        assert result == True
        # Should only process document and entity, skip invalid relations
        assert self.mock_transaction.run.call_count == 2

    def test_clean_relation_type(self):
        """Test relation type cleaning for Neo4j compatibility"""
        with patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver') as mock_graph_driver:
            mock_graph_driver.return_value = self.mock_driver
            service = Neo4jService(self.config)

            # Test various relation types
            assert service._clean_relation_type("used for") == "USED_FOR"
            assert service._clean_relation_type("is-a") == "IS_A"
            assert service._clean_relation_type("related to!") == "RELATED_TO"
            assert service._clean_relation_type("@#$%") == "RELATED_TO"  # All special chars
            assert service._clean_relation_type("") == "RELATED_TO"  # Empty string

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_get_document_entities(self, mock_graph_driver):
        """Test retrieving document entities"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Mock query result
        mock_result = MagicMock()
        mock_records = [
            {"entity_name": "Python"},
            {"entity_name": "Machine Learning"}
        ]
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        self.mock_session.run.return_value = mock_result

        entities = service.get_document_entities("doc_123")

        assert len(entities) == 2
        assert entities[0]["name"] == "Python"
        assert entities[1]["name"] == "Machine Learning"

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_get_document_relationships(self, mock_graph_driver):
        """Test retrieving document relationships"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Mock query result
        mock_result = MagicMock()
        mock_records = [
            {
                "source": "Python",
                "target": "Machine Learning",
                "relation_type": "USED_FOR",
                "original_relation": "used for"
            }
        ]
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        self.mock_session.run.return_value = mock_result

        relationships = service.get_document_relationships("doc_123")

        assert len(relationships) == 1
        assert relationships[0]["source"] == "Python"
        assert relationships[0]["target"] == "Machine Learning"
        assert relationships[0]["relation_type"] == "USED_FOR"

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_search_entities(self, mock_graph_driver):
        """Test entity search functionality"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Mock query result
        mock_result = MagicMock()
        mock_records = [
            {
                "entity_name": "Python Programming",
                "documents": ["doc_1", "doc_2"]
            }
        ]
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        self.mock_session.run.return_value = mock_result

        entities = service.search_entities("python", limit=5)

        assert len(entities) == 1
        assert entities[0]["name"] == "Python Programming"
        assert entities[0]["documents"] == ["doc_1", "doc_2"]

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_get_entity_connections(self, mock_graph_driver):
        """Test getting entity connections"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Mock query result
        mock_result = MagicMock()
        mock_records = [
            {"connected_entity": "Machine Learning", "distance": 1},
            {"connected_entity": "Data Science", "distance": 2}
        ]
        mock_result.__iter__ = Mock(return_value=iter(mock_records))
        self.mock_session.run.return_value = mock_result

        connections = service.get_entity_connections("Python", depth=2)

        assert len(connections) == 2
        assert connections[0]["entity"] == "Machine Learning"
        assert connections[0]["distance"] == 1
        assert connections[1]["entity"] == "Data Science"
        assert connections[1]["distance"] == 2

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_delete_document_graph(self, mock_graph_driver):
        """Test deleting document graph"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        result = service.delete_document_graph("doc_123")

        assert result == True
        assert self.mock_transaction.run.call_count == 3  # Delete relationships, entities, document

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_get_graph_statistics(self, mock_graph_driver):
        """Test getting graph statistics"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Mock query results
        mock_entity_result = MagicMock()
        mock_entity_result.single.return_value = {"count": 100}

        mock_doc_result = MagicMock()
        mock_doc_result.single.return_value = {"count": 10}

        mock_rel_result = MagicMock()
        mock_rel_result.single.return_value = {"count": 250}

        self.mock_session.run.side_effect = [
            mock_entity_result,
            mock_doc_result,
            mock_rel_result
        ]

        stats = service.get_graph_statistics()

        assert stats["entities"] == 100
        assert stats["documents"] == 10
        assert stats["relationships"] == 250

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_test_connection_success(self, mock_graph_driver):
        """Test successful connection test"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        mock_result = MagicMock()
        mock_result.single.return_value = {"status": "Connection OK"}
        self.mock_session.run.return_value = mock_result

        result = service.test_connection()

        assert result == True

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_test_connection_failure(self, mock_graph_driver):
        """Test failed connection test"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        self.mock_session.run.side_effect = Exception("Connection failed")

        result = service.test_connection()

        assert result == False

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_context_manager(self, mock_graph_driver):
        """Test using Neo4j service as context manager"""
        mock_graph_driver.return_value = self.mock_driver

        with Neo4jService(self.config) as service:
            assert service.driver == self.mock_driver

        # Should have called close
        self.mock_driver.close.assert_called_once()

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_error_handling_in_save(self, mock_graph_driver):
        """Test error handling during knowledge graph save"""
        from neo4j.exceptions import Neo4jError
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        self.mock_transaction.run.side_effect = Neo4jError("Database error")

        result = service.save_knowledge_graph("doc_123", {"entities": set(), "relations": []})

        assert result == False

    @patch('knowledge_graph.core.db.neo4j.service.GraphDatabase.driver')
    def test_empty_kg_graph_handling(self, mock_graph_driver):
        """Test handling of empty knowledge graph"""
        mock_graph_driver.return_value = self.mock_driver
        service = Neo4jService(self.config)

        # Empty graph
        kg_graph = {'entities': set(), 'relations': []}
        result = service.save_knowledge_graph("doc_123", kg_graph)

        assert result == True
        # Should still create document node
        assert self.mock_transaction.run.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])