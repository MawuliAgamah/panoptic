#!/usr/bin/env python3
"""
Main entry point for the AI Module application.
"""
import asyncio
import logging
import sys
import os
from typing import Optional

from bots import get_telegram_bot
from knowledge_graph import create_json_client, KnowledgeGraphClient
import dotenv


async def run_telegram_bot():
    """Run the Telegram bot."""
    try:
        TelegramBot = get_telegram_bot()
        bot = TelegramBot()
        await bot.run_forever()
    except KeyboardInterrupt:
        logging.info("Telegram bot stopped by user")
    except Exception as e:
        logging.error(f"Telegram bot error: {e}")
        raise


async def process_document(document_path: str):
    """Process a document through the complete KG pipeline using refactored client."""
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Processing document: {document_path}")

        # Validate file exists
        if not os.path.exists(document_path):
            logger.error(f"File not found: {document_path}")
            return

        file_size = os.path.getsize(document_path)
        filename = os.path.basename(document_path)
        logger.info(f"File found: {filename} ({file_size:,} bytes)")

        # Load environment variables
        dotenv.load_dotenv()

        # Auto-detect LLM provider
        if os.getenv("OPENAI_API_KEY"):
            llm_provider = "openai"
        elif os.getenv("KG_LLM_PROVIDER") == "ollama":
            llm_provider = "ollama"
        else:
            logger.warning("No LLM provider configured. Using mock extraction.")
            llm_provider = "mock"

        logger.info(f"Using LLM provider: {llm_provider}")

        # Generate document ID from filename
        doc_id = f"processed_{filename.replace('.', '_').replace(' ', '_').lower()}"
        logger.info(f"Document ID: {doc_id}")

        # Initialize JSON client with kggen integration
        openai_api_key = os.getenv("OPENAI_API_KEY") if llm_provider == "openai" else None

        with create_json_client(openai_api_key=openai_api_key) as client:
            logger.info("Initialized JSON knowledge graph client with kggen")

            # Add document to the knowledge graph system
            try:
                document_id = client.add_document(
                    document_path=document_path,
                    document_id=doc_id,
                    document_type=None  # Auto-detect
                )
                logger.info(f"Document added with ID: {document_id}")
            except Exception as e:
                logger.error(f"Failed to add document: {e}")
                return

            # Extract ontology using kggen integration
            try:
                logger.info("Starting ontology extraction with kggen")
                client.extract_document_ontology(document_id)
                logger.info("Ontology extraction completed")
            except Exception as e:
                logger.error(f"Ontology extraction failed: {e}")
                return

            # Get the processed document for stats
            try:
                document_obj = client.get_cached_document(document_id)
                if document_obj:
                    logger.info("Document processing statistics:")
                    logger.info(f"  Title: {document_obj.title}")
                    logger.info(f"  File size: {document_obj.file_size:,} bytes")
                    logger.info(f"  Content length: {len(document_obj.raw_content):,} chars")
                    logger.info(f"  Text chunks: {len(document_obj.textChunks)}")

                    # Processing status
                    statuses = [
                        ("Parsed", document_obj.is_parsed),
                        ("Cleaned", document_obj.is_preprocessed),
                        ("Chunked", document_obj.is_chunked),
                        ("Metadata Generated", document_obj.is_metadata_generated),
                        ("KG Extracted", document_obj.is_kg_extracted)
                    ]

                    for status_name, status_value in statuses:
                        status_text = "COMPLETE" if status_value else "PENDING"
                        logger.info(f"  {status_name}: {status_text}")

            except Exception as e:
                logger.warning(f"Could not retrieve document stats: {e}")

            # Get knowledge graph statistics
            try:
                stats = client.get_knowledge_graph_stats()
                logger.info("Knowledge graph statistics:")
                logger.info(f"  Total entities: {stats.get('total_entities', 0)}")
                logger.info(f"  Total relationships: {stats.get('total_relationships', 0)}")
                logger.info(f"  Unique documents: {stats.get('unique_documents', 0)}")
                logger.info(f"  Last updated: {stats.get('last_updated', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Could not retrieve knowledge graph stats: {e}")

            # Demonstrate advanced kggen extraction on sample text
            try:
                sample_text = f"Document processed: {filename}. This document contains knowledge about various topics and concepts."

                kg_result = client.extract_knowledge_graph_advanced(
                    text=sample_text,
                    strategy="detailed"
                )

                logger.info("Advanced extraction sample:")
                logger.info(f"  Entities found: {len(kg_result.get('entities', []))}")
                logger.info(f"  Relations found: {len(kg_result.get('relations', []))}")

                if 'metadata' in kg_result:
                    extraction_time = kg_result['metadata'].get('extraction_time', 0)
                    logger.info(f"  Extraction time: {extraction_time:.2f}s")

            except Exception as e:
                logger.warning(f"Advanced extraction sample failed: {e}")

            # Save results to file
            try:
                output_file = f"{doc_id}_results.txt"
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(f"Knowledge Graph Processing Results\n")
                    f.write(f"Document: {filename}\n")
                    f.write(f"Document ID: {document_id}\n")
                    f.write(f"LLM Provider: {llm_provider}\n")
                    f.write(f"Processing completed successfully.\n\n")

                    f.write("Knowledge Graph Statistics:\n")
                    for key, value in stats.items():
                        f.write(f"  {key}: {value}\n")

                logger.info(f"Results saved to: {output_file}")

            except Exception as e:
                logger.warning(f"Failed to save results file: {e}")

        logger.info("Document processing completed successfully")

    except Exception as e:
        logger.error(f"Document processing error: {e}")
        raise


async def clear_knowledge_store():
    """Clear all data from the JSON knowledge store."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("Clearing knowledge store...")

        with create_json_client() as client:
            # Get current stats before clearing
            stats = client.get_knowledge_graph_stats()
            logger.info("Current store statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")

            # Note: Would need to implement a clear method in the client
            logger.warning("Clear functionality would need to be implemented in the client")
            logger.info("Knowledge store clearing would be completed here")

    except Exception as e:
        logger.error(f"Knowledge store clear error: {e}")
        raise


async def query_knowledge_store(query: str):
    """Query the JSON knowledge store using refactored client."""
    logger = logging.getLogger(__name__)

    try:
        logger.info(f"Querying knowledge store: '{query}'")

        with create_json_client() as client:
            # Query using natural language
            results = client.query(query)
            logger.info(f"Query results: {results['total_results']} total results")

            # Search entities
            entities = client.search_entities(query)
            logger.info(f"Entities found: {len(entities)}")
            for i, entity in enumerate(entities[:5], 1):  # Show first 5
                logger.info(f"  {i}. {entity['name']} (type: {entity['type']})")
                logger.info(f"     Documents: {len(entity.get('document_ids', []))}")

            if len(entities) > 5:
                logger.info(f"     ... and {len(entities) - 5} more entities")

            # Search relationships
            relationships = client.search_relationships(query)
            logger.info(f"Relationships found: {len(relationships)}")
            for i, rel in enumerate(relationships[:5], 1):  # Show first 5
                logger.info(f"  {i}. {rel['source_entity']} --[{rel['relation_type']}]--> {rel['target_entity']}")
                logger.info(f"     Documents: {len(rel.get('document_ids', []))}")

            if len(relationships) > 5:
                logger.info(f"     ... and {len(relationships) - 5} more relationships")

            # Get overall statistics
            stats = client.get_knowledge_graph_stats()
            logger.info("Knowledge graph statistics:")
            for key, value in stats.items():
                logger.info(f"  {key}: {value}")

        logger.info("Query completed successfully")

    except Exception as e:
        logger.error(f"Knowledge store query error: {e}")
        raise


async def main():
    """Main application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "telegram":
            await run_telegram_bot()
        elif command == "process" and len(sys.argv) > 2:
            document_path = sys.argv[2]
            await process_document(document_path)
        elif command == "process":
            logging.error("Please provide a document path")
            print("Usage: python src/main.py process <document_path>")
        elif command == "query" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])  # Join all remaining args as query
            await query_knowledge_store(query)
        elif command == "query":
            logging.error("Please provide a query")
            print("Usage: python src/main.py query <search_terms>")
        elif command == "clear_kg_store":
            await clear_knowledge_store()
        else:
            logging.error(f"Unknown command: {command}")
            print_usage()
    else:
        print_usage()


def print_usage():
    """Print usage information."""
    print("AI Module - Usage:")
    print("  python src/main.py telegram                    # Run Telegram bot")
    print("  python src/main.py process <document_path>     # Process document through KG pipeline")
    print("  python src/main.py query <search_terms>       # Query the JSON knowledge store")
    print("  python src/main.py clear_kg_store              # Clear all data from knowledge store")
    print("")
    print("Examples:")
    print('  python src/main.py process "/path/to/document.md"')
    print('  python src/main.py process "~/Documents/notes.txt"')
    print('  python src/main.py query "machine learning"')
    print('  python src/main.py query "Python programming"')
    print("")
    print("LLM Provider Configuration:")
    print("  export OPENAI_API_KEY=your-api-key    # Use OpenAI GPT models")
    print("  export KG_LLM_PROVIDER=ollama         # Use local Ollama")
    print("")
    print("Full Example with OpenAI:")
    print('  export OPENAI_API_KEY="your-api-key"')
    print('  python src/main.py process "/path/to/document.md"')
    print("")
    print("Knowledge Store Features:")
    print("  - JSON-based storage (no database server required)")
    print("  - Advanced kggen integration for entity extraction")
    print("  - Automatic deduplication across documents")
    print("  - Natural language querying capabilities")
    print("  - Comprehensive logging for debugging")
    print("")
    print("Supported formats: .md, .txt, .pdf, .docx")
    print("The system will automatically:")
    print("  - Clean and parse the document")
    print("  - Extract entities and relationships using kggen")
    print("  - Generate metadata and topics")
    print("  - Save to JSON knowledge store")
    print("  - Create detailed result files")


if __name__ == "__main__":
    asyncio.run(main())