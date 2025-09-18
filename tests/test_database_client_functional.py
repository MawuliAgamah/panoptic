"""
Functional test for DatabaseClient - tests real functionality without mocking
"""
import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from knowledge_graph.core.db.db_client import DatabaseClient

def test_sqlite_only_configuration():
    """Test DatabaseClient with SQLite-only configuration"""
    config = {
        'sqlite': {
            'db_location': '/tmp/test.db'
        }
    }

    # This should work without Neo4j configured
    client = DatabaseClient(config)

    assert client.sqlite_service is not None
    assert client.neo4j_service is None

    # Test knowledge graph operations gracefully fail
    result = client.save_knowledge_graph("doc_123", {"entities": set(), "relations": []})
    assert result == False  # Should return False when Neo4j not available

    entities = client.search_entities("test")
    assert entities == []  # Should return empty list when Neo4j not available

    stats = client.get_graph_statistics()
    assert stats == {"entities": 0, "documents": 0, "relationships": 0}

def test_neo4j_unavailable_configuration():
    """Test DatabaseClient when Neo4j connection fails"""
    config = {
        'sqlite': {
            'db_location': '/tmp/test.db'
        },
        'neo4j': {
            'host': 'nonexistent_host',
            'port': 9999,
            'username': 'test',
            'password': 'test',
            'database': 'test'
        }
    }

    # This should work with SQLite and gracefully handle Neo4j failure
    client = DatabaseClient(config)

    assert client.sqlite_service is not None
    assert client.neo4j_service is None  # Should be None due to connection failure

    # Test knowledge graph operations gracefully fail
    result = client.save_knowledge_graph("doc_123", {"entities": set(), "relations": []})
    assert result == False

def test_no_database_fails():
    """Test that initialization fails when no databases are configured"""
    config = {}

    with pytest.raises(ValueError, match="At least one database service must be configured"):
        DatabaseClient(config)

def test_connection_testing():
    """Test connection testing functionality"""
    config = {
        'sqlite': {
            'db_location': '/tmp/test.db'
        }
    }

    client = DatabaseClient(config)
    results = client.test_connections()

    assert 'sqlite' in results
    assert 'neo4j' in results
    assert results['sqlite'] == True  # SQLite should work
    assert results['neo4j'] == False  # Neo4j should be unavailable


if __name__ == "__main__":
    pytest.main([__file__, "-v"])