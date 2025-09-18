import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.core.db.db_client import DatabaseClient

class TestDatabaseClient:
    """Test dual database client implementation"""

    def setup_method(self):
        """Setup test environment with mock services"""
        self.sqlite_config = {
            'sqlite': {
                'db_location': '/test/test.db'
            }
        }

        self.neo4j_config = {
            'neo4j': {
                'host': 'localhost',
                'port': 7687,
                'username': 'neo4j',
                'password': 'password',
                'database': 'test_db'
            }
        }

        self.dual_config = {
            'sqlite': {
                'db_location': '/test/test.db'
            },
            'neo4j': {
                'host': 'localhost',
                'port': 7687,
                'username': 'neo4j',
                'password': 'password',
                'database': 'test_db'
            }
        }

        # Mock services
        self.mock_sqlite_service = MagicMock()
        self.mock_neo4j_service = MagicMock()

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_sqlite_only_initialization(self, mock_sqlite_cls):
        """Test initialization with SQLite only"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service

        client = DatabaseClient(self.sqlite_config)

        assert client.sqlite_service == self.mock_sqlite_service
        assert client.neo4j_service is None
        mock_sqlite_cls.assert_called_once_with(db_path='/test/test.db')

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    def test_neo4j_only_initialization(self, mock_neo4j_cls):
        """Test initialization with Neo4j only"""
        mock_neo4j_cls.return_value = self.mock_neo4j_service

        client = DatabaseClient(self.neo4j_config)

        assert client.sqlite_service is None
        assert client.neo4j_service == self.mock_neo4j_service
        mock_neo4j_cls.assert_called_once_with(self.neo4j_config['neo4j'])

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_dual_database_initialization(self, mock_sqlite_cls, mock_neo4j_cls):
        """Test initialization with both databases"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service
        mock_neo4j_cls.return_value = self.mock_neo4j_service

        client = DatabaseClient(self.dual_config)

        assert client.sqlite_service == self.mock_sqlite_service
        assert client.neo4j_service == self.mock_neo4j_service

    def test_no_database_initialization(self):
        """Test initialization failure with no databases configured"""
        with pytest.raises(ValueError, match="At least one database service must be configured"):
            DatabaseClient({})

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_neo4j_initialization_failure(self, mock_sqlite_cls, mock_neo4j_cls):
        """Test handling of Neo4j initialization failure"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service
        mock_neo4j_cls.side_effect = Exception("Neo4j connection failed")

        client = DatabaseClient(self.dual_config)

        assert client.sqlite_service == self.mock_sqlite_service
        assert client.neo4j_service is None

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_save_document(self, mock_sqlite_cls):
        """Test document saving to SQLite"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service
        self.mock_sqlite_service.save_document.return_value = True

        client = DatabaseClient(self.sqlite_config)
        document = MagicMock()

        result = client.save_document(document)

        assert result == True
        self.mock_sqlite_service.save_document.assert_called_once_with(document)

    def test_save_document_no_sqlite(self):
        """Test document saving failure when SQLite not configured"""
        client = DatabaseClient({})
        client.sqlite_service = None
        document = MagicMock()

        with pytest.raises(ValueError, match="SQLite service not initialized"):
            client.save_document(document)

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_delete_document_dual(self, mock_sqlite_cls, mock_neo4j_cls):
        """Test document deletion from both databases"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service
        mock_neo4j_cls.return_value = self.mock_neo4j_service

        self.mock_sqlite_service.delete_document.return_value = True
        self.mock_neo4j_service.delete_document_graph.return_value = True

        client = DatabaseClient(self.dual_config)
        result = client.delete_document("doc_123")

        assert result['sqlite'] == True
        assert result['neo4j'] == True
        self.mock_sqlite_service.delete_document.assert_called_once_with("doc_123")
        self.mock_neo4j_service.delete_document_graph.assert_called_once_with("doc_123")

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_get_document(self, mock_sqlite_cls):
        """Test document retrieval"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service

        # Mock document data structure
        mock_doc_data = {
            'document': [('doc_123', '/test/doc.md', 'hash123', '.md', 'Test Doc',
                         'Summary', 'Raw content', 'Clean content',
                         '2024-01-01', '2024-01-02', '2024-01-03')],
            'chunks': []
        }
        self.mock_sqlite_service.retrieve_document.return_value = mock_doc_data

        client = DatabaseClient(self.sqlite_config)
        document = client.get_document("doc_123")

        assert document is not None
        assert document.id == "doc_123"
        assert document.title == "Test Doc"
        assert document.raw_content == "Raw content"
        assert document.clean_content == "Clean content"

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    def test_save_knowledge_graph(self, mock_neo4j_cls):
        """Test knowledge graph saving to Neo4j"""
        mock_neo4j_cls.return_value = self.mock_neo4j_service
        self.mock_neo4j_service.save_knowledge_graph.return_value = True

        client = DatabaseClient(self.neo4j_config)
        kg_graph = {'entities': set(['Python']), 'relations': []}

        result = client.save_knowledge_graph("doc_123", kg_graph)

        assert result == True
        self.mock_neo4j_service.save_knowledge_graph.assert_called_once_with("doc_123", kg_graph)

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_save_knowledge_graph_no_neo4j(self, mock_sqlite_cls):
        """Test knowledge graph saving when Neo4j not available"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service

        client = DatabaseClient(self.sqlite_config)
        kg_graph = {'entities': set(['Python']), 'relations': []}

        result = client.save_knowledge_graph("doc_123", kg_graph)

        assert result == False  # Should return False when Neo4j not available

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    def test_search_entities(self, mock_neo4j_cls):
        """Test entity search in Neo4j"""
        mock_neo4j_cls.return_value = self.mock_neo4j_service
        mock_entities = [{'name': 'Python', 'documents': ['doc_1']}]
        self.mock_neo4j_service.search_entities.return_value = mock_entities

        client = DatabaseClient(self.neo4j_config)
        results = client.search_entities("python", limit=5)

        assert results == mock_entities
        self.mock_neo4j_service.search_entities.assert_called_once_with("python", 5)

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    def test_get_entity_connections(self, mock_neo4j_cls):
        """Test getting entity connections"""
        mock_neo4j_cls.return_value = self.mock_neo4j_service
        mock_connections = [{'entity': 'Machine Learning', 'distance': 1}]
        self.mock_neo4j_service.get_entity_connections.return_value = mock_connections

        client = DatabaseClient(self.neo4j_config)
        results = client.get_entity_connections("Python", depth=2)

        assert results == mock_connections
        self.mock_neo4j_service.get_entity_connections.assert_called_once_with("Python", 2)

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    def test_get_graph_statistics(self, mock_neo4j_cls):
        """Test getting graph statistics"""
        mock_neo4j_cls.return_value = self.mock_neo4j_service
        mock_stats = {'entities': 100, 'documents': 10, 'relationships': 250}
        self.mock_neo4j_service.get_graph_statistics.return_value = mock_stats

        client = DatabaseClient(self.neo4j_config)
        results = client.get_graph_statistics()

        assert results == mock_stats

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_get_graph_statistics_no_neo4j(self, mock_sqlite_cls):
        """Test getting graph statistics when Neo4j not available"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service

        client = DatabaseClient(self.sqlite_config)
        results = client.get_graph_statistics()

        expected = {"entities": 0, "documents": 0, "relationships": 0}
        assert results == expected

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_test_connections(self, mock_sqlite_cls, mock_neo4j_cls):
        """Test connection testing for both databases"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service
        mock_neo4j_cls.return_value = self.mock_neo4j_service
        self.mock_neo4j_service.test_connection.return_value = True

        client = DatabaseClient(self.dual_config)
        results = client.test_connections()

        assert results['sqlite'] == True
        assert results['neo4j'] == True

    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_legacy_ontology_methods(self, mock_sqlite_cls):
        """Test legacy ontology methods delegate to SQLite"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service
        self.mock_sqlite_service.save_document_ontology.return_value = True

        client = DatabaseClient(self.sqlite_config)
        ontology = {'entities': [], 'relations': []}

        result = client.save_document_ontology("doc_123", ontology)

        assert result == True
        self.mock_sqlite_service.save_document_ontology.assert_called_once_with("doc_123", ontology)

    @patch('knowledge_graph.core.db.neo4j.service.Neo4jService')
    @patch('knowledge_graph.core.db.sql_lite.service.SQLLiteService')
    def test_context_manager(self, mock_sqlite_cls, mock_neo4j_cls):
        """Test using DatabaseClient as context manager"""
        mock_sqlite_cls.return_value = self.mock_sqlite_service
        mock_neo4j_cls.return_value = self.mock_neo4j_service

        with DatabaseClient(self.dual_config) as client:
            assert client.sqlite_service == self.mock_sqlite_service
            assert client.neo4j_service == self.mock_neo4j_service

        # Should have called close on Neo4j service
        self.mock_neo4j_service.close.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])