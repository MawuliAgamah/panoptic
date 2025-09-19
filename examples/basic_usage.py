#!/usr/bin/env python3
"""
Basic usage examples for the refactored KnowledgeGraphClient.
Demonstrates both new and legacy configuration approaches.
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.knowledge_graph import (
    KnowledgeGraphClient,
    KnowledgeGraphConfig,
    DatabaseConfig,
    LLMConfig,
    create_client
)

def example_1_simple_usage():
    """Example 1: Simplest way to create a client"""
    print("=== Example 1: Simple Usage ===")

    # This is the easiest way to get started
    with create_client(
        neo4j_uri="bolt://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        openai_api_key=os.getenv("OPENAI_API_KEY")
    ) as client:
        # Add a document
        doc_id = client.add_document(
            document_path="./sample_documents/sample.md",
            document_id="example_doc_1",
            document_type="markdown"
        )

        # Extract ontology using kggen
        client.extract_document_ontology(doc_id)

        # Advanced KG extraction
        kg_result = client.extract_knowledge_graph_advanced(
            text="Python is a programming language created by Guido van Rossum.",
            strategy="detailed"
        )
        print(f"Extracted {len(kg_result['entities'])} entities")

def example_2_new_config():
    """Example 2: Using new unified configuration"""
    print("\n=== Example 2: New Configuration System ===")

    # Create configuration object
    config = KnowledgeGraphConfig(
        graph_db=DatabaseConfig(
            db_type="neo4j",
            host="localhost",
            port=7687,
            username="neo4j",
            password="password",
            database="neo4j"
        ),
        llm=LLMConfig(
            provider="openai",
            model="gpt-3.5-turbo",
            temperature=0.2
        ),
        log_level="INFO"
    )

    # Create client with unified config
    with KnowledgeGraphClient(config=config) as client:
        print("Client created with new configuration system")

        # Use advanced KG extraction features
        result = client.extract_knowledge_graph_advanced(
            text="Neo4j is a graph database. OpenAI provides language models.",
            strategy="detailed"
        )
        print(f"Extracted: {result['entities']}")

def example_3_legacy_compatibility():
    """Example 3: Legacy configuration (backward compatibility)"""
    print("\n=== Example 3: Legacy Configuration ===")

    # This still works exactly as before
    client = KnowledgeGraphClient(
        graph_db_config={
            "db_type": "neo4j",
            "host": "localhost",
            "port": 7687,
            "database": "neo4j",
            "username": "neo4j",
            "password": "password"
        },
        db_config={
            "db_type": "sqlite",
            "db_location": "./data/cache.db"
        },
        llm_config={
            "model": "gpt-3.5-turbo",
            "temperature": 0.2,
            "api_key": os.getenv("OPENAI_API_KEY")
        }
    )

    print("Client created with legacy configuration")
    client.close()

def example_4_config_from_file():
    """Example 4: Configuration from file"""
    print("\n=== Example 4: Configuration from File ===")

    # Create a sample config file
    config_content = """
graph_db:
  db_type: neo4j
  host: localhost
  port: 7687
  username: neo4j
  password: password
  database: neo4j

llm:
  provider: openai
  model: gpt-3.5-turbo
  temperature: 0.2

log_level: INFO
"""

    # Save config to file
    config_path = project_root / "config_example.yaml"
    with open(config_path, 'w') as f:
        f.write(config_content)

    try:
        # Create client from config file
        with KnowledgeGraphClient.from_config_file(config_path) as client:
            print("Client created from YAML config file")
    except Exception as e:
        print(f"Note: Install PyYAML to use config files: {e}")
    finally:
        # Clean up
        if config_path.exists():
            config_path.unlink()

def example_5_kggen_integration():
    """Example 5: Advanced KGGen integration"""
    print("\n=== Example 5: KGGen Integration ===")

    with create_client() as client:
        # Different extraction strategies
        text = """
        Artificial Intelligence (AI) is transforming healthcare.
        Companies like OpenAI and Google are developing large language models.
        These models can assist doctors in diagnosing diseases and analyzing medical images.
        """

        # Simple extraction
        simple_result = client.extract_knowledge_graph_advanced(
            text=text,
            strategy="simple"
        )

        # Detailed extraction with clustering
        detailed_result = client.extract_knowledge_graph_advanced(
            text=text,
            strategy="detailed"
        )

        print(f"Simple: {len(simple_result['entities'])} entities")
        print(f"Detailed: {len(detailed_result['entities'])} entities")

        if 'metadata' in detailed_result:
            print(f"Extraction took: {detailed_result['metadata']['extraction_time']:.2f}s")

if __name__ == "__main__":
    print("KnowledgeGraphClient - Refactored Usage Examples")
    print("=" * 50)

    try:
        example_1_simple_usage()
        example_2_new_config()
        example_3_legacy_compatibility()
        example_4_config_from_file()
        example_5_kggen_integration()

        print("\n✅ All examples completed successfully!")
        print("\nNow you can import the client in other modules like:")
        print("from src.knowledge_graph import KnowledgeGraphClient, create_client")

    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("Make sure Neo4j is running and OpenAI API key is set")