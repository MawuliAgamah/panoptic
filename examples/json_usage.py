#!/usr/bin/env python3
"""
JSON Knowledge Graph Storage Examples
Demonstrates using JSON instead of Neo4j for knowledge graph storage.
"""

import os
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

from src.knowledge_graph import (
    KnowledgeGraphClient,
    create_client,
    create_json_client,
    KnowledgeGraphConfig,
    DatabaseConfig,
    LLMConfig
)

def example_1_simple_json_client():
    """Example 1: Using JSON storage with default settings"""
    print("=== Example 1: Simple JSON Client ===")

    # This creates a client that stores knowledge graphs in JSON format
    with create_client(
        graph_db_type="json",  # Use JSON instead of Neo4j
        openai_api_key=os.getenv("OPENAI_API_KEY")
    ) as client:
        print(f"Graph DB type: {client.db_client.graph_db_type}")

        # Add a document
        doc_id = client.add_document(
            document_path="./sample_documents/sample.md",
            document_id="json_example_doc",
            document_type="markdown"
        )
        print(f"Added document: {doc_id}")

        # Extract ontology (this will be stored in JSON)
        client.extract_document_ontology(doc_id)

        # Query the knowledge graph
        stats = client.get_knowledge_graph_stats()
        print(f"Knowledge Graph Stats: {stats}")

def example_2_custom_json_file():
    """Example 2: Using JSON storage with custom file location"""
    print("\n=== Example 2: Custom JSON File Location ===")

    custom_json_path = "./my_custom_kg.json"

    with create_json_client(
        data_file=custom_json_path,
        openai_api_key=os.getenv("OPENAI_API_KEY")
    ) as client:
        print(f"Using JSON file: {custom_json_path}")

        # Add knowledge directly using kggen
        kg_result = client.extract_knowledge_graph_advanced(
            text="""
            Python is a programming language created by Guido van Rossum in 1991.
            It is used for web development, data science, and artificial intelligence.
            Companies like Google, Netflix, and Instagram use Python extensively.
            """,
            strategy="detailed"
        )

        print(f"Extracted {len(kg_result['entities'])} entities:")
        for entity in kg_result['entities']:
            print(f"  - {entity}")

def example_3_json_configuration():
    """Example 3: Using configuration objects for JSON storage"""
    print("\n=== Example 3: JSON Configuration Object ===")

    config = KnowledgeGraphConfig(
        graph_db=DatabaseConfig(
            db_type="json",
            data_file="./enterprise_knowledge_graph.json"
        ),
        llm=LLMConfig(
            provider="openai",
            model="gpt-4",
            temperature=0.1
        )
    )

    with KnowledgeGraphClient(config=config) as client:
        print("Client created with full configuration object")

        # Show some querying capabilities
        # First, let's add some sample data
        sample_text = """
        OpenAI developed ChatGPT using transformer architecture.
        The model is based on GPT-3.5 and GPT-4 technology.
        It can be used for natural language processing tasks.
        """

        kg_data = client.extract_knowledge_graph_advanced(sample_text)
        print(f"Sample extraction: {len(kg_data['entities'])} entities")

def example_4_json_querying():
    """Example 4: Querying the JSON knowledge graph"""
    print("\n=== Example 4: Querying JSON Knowledge Graph ===")

    with create_json_client() as client:
        # Add some sample knowledge
        texts = [
            "Python is a programming language developed by Guido van Rossum.",
            "TensorFlow is a machine learning framework created by Google.",
            "PyTorch is another ML framework developed by Facebook.",
        ]

        for i, text in enumerate(texts):
            client.extract_knowledge_graph_advanced(text)

        # Query the knowledge graph
        queries = [
            "Python",
            "machine learning",
            "Google",
            "programming"
        ]

        for query in queries:
            results = client.query(query)
            print(f"\nQuery: '{query}'")
            print(f"  Found {results['total_results']} results")

            # Search specific entity types
            entities = client.search_entities(query)
            if entities:
                print(f"  Entities: {[e['name'] for e in entities[:3]]}")

            relationships = client.search_relationships(query)
            if relationships:
                print(f"  Relationships: {len(relationships)} found")

def example_5_comparison():
    """Example 5: Comparing JSON vs Neo4j configurations"""
    print("\n=== Example 5: JSON vs Neo4j Configuration Comparison ===")

    print("JSON Configuration (File-based, simple setup):")
    json_config = {
        'graph_db': {
            'db_type': 'json',
            'data_file': './my_kg.json'
        },
        'llm': {
            'provider': 'openai'
        }
    }
    print(f"  {json_config}")

    print("\nNeo4j Configuration (Server-based, more complex setup):")
    neo4j_config = {
        'graph_db': {
            'db_type': 'neo4j',
            'host': 'localhost',
            'port': 7687,
            'username': 'neo4j',
            'password': 'password',
            'database': 'neo4j'
        },
        'llm': {
            'provider': 'openai'
        }
    }
    print(f"  {neo4j_config}")

    print("\nJSON Benefits:")
    print("  ✅ No server setup required")
    print("  ✅ Portable - just a file")
    print("  ✅ Easy backup and version control")
    print("  ✅ Good for development and small projects")

    print("\nNeo4j Benefits:")
    print("  ✅ Better performance for large graphs")
    print("  ✅ Advanced graph query capabilities")
    print("  ✅ Concurrent access support")
    print("  ✅ Enterprise features")

if __name__ == "__main__":
    print("JSON Knowledge Graph Storage Examples")
    print("=" * 50)

    try:
        example_1_simple_json_client()
        example_2_custom_json_file()
        example_3_json_configuration()
        example_4_json_querying()
        example_5_comparison()

        print("\n✅ All JSON examples completed successfully!")
        print("\nYour knowledge graph data is now stored in JSON files.")
        print("You can inspect the files to see the extracted entities and relationships.")

    except Exception as e:
        print(f"\n❌ Example failed: {e}")
        print("Make sure OpenAI API key is set if using real extraction")