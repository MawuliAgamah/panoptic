#!/usr/bin/env python3
"""
Main entry point for the AI Module application.
"""
import asyncio
import logging
import sys
import os
from typing import Optional
from unittest.mock import MagicMock

from bots import get_telegram_bot
from knowledge_graph.document.manager.document_manager import DocumentManager
from knowledge_graph.llm.kg_extractor.service import KGExtractionService
from services.knowledge_store import JsonKnowledgeStore


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
    """Process a document through the complete KG pipeline."""
    try:
        print(f"🚀 Processing document: {document_path}")

        # Validate file exists
        if not os.path.exists(document_path):
            print(f"❌ Error: File not found: {document_path}")
            return

        print(f"✅ File found: {os.path.basename(document_path)} ({os.path.getsize(document_path):,} bytes)")

        # Setup services
        print("🔧 Initializing services...")

        # Mock LLM service for topic/keyword extraction
        mock_llm_service = MagicMock()
        mock_llm_service.extract_topics.return_value = {
            "topics": ["document", "analysis", "knowledge", "information", "content"]
        }
        mock_llm_service.extract_keywords.return_value = {
            "keywords": ["text", "data", "processing", "analysis", "extraction"]
        }

        # Initialize KG service (configure LLM provider)
        # Auto-detect provider based on available configuration
        # Priority: OpenAI (if API key available) -> Ollama -> Mock

        # Check for .env file and load it
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        os.environ[key.strip()] = value.strip()

        # Auto-select provider
        if os.getenv("OPENAI_API_KEY"):
            llm_provider = "openai"
        elif os.getenv("KG_LLM_PROVIDER"):
            llm_provider = os.getenv("KG_LLM_PROVIDER")
        else:
            print("❌ No LLM provider configured. Please set OPENAI_API_KEY or KG_LLM_PROVIDER.")
            return

        print(f"🧠 Using LLM provider: {llm_provider}")

        kg_service_config = {}
        if llm_provider == "openai":
            kg_service_config = {
                'model': 'gpt-3.5-turbo',
                'max_tokens': 1000
            }
        elif llm_provider == "ollama":
            kg_service_config = {
                'model': 'llama3.2:3b',
                'max_tokens': 1000
            }

        kg_service = KGExtractionService(llm_provider=llm_provider, **kg_service_config)

        # Initialize DocumentManager with KG integration
        doc_manager = DocumentManager(
            llm_service=mock_llm_service,
            kg_service=kg_service
        )

        # Initialize JSON Knowledge Store
        json_store = JsonKnowledgeStore()
        print("✅ Services initialized (including JSON Knowledge Store)")

        # Generate document ID from filename
        filename = os.path.basename(document_path)
        doc_id = f"processed_{filename.replace('.', '_').replace(' ', '_').lower()}"

        print(f"📄 Processing document ID: {doc_id}")

        # Process through complete pipeline
        document = doc_manager.process_document_complete(
            document_path=document_path,
            document_id=doc_id,
            enable_kg_extraction=True,
            enable_enrichment=True  # Enable LLM enrichment
        )

        if document is None:
            print("❌ Failed to process document")
            return

        print("\n" + "="*50)
        print("📊 PROCESSING RESULTS")
        print("="*50)

        # Document info
        print(f"📄 Title: {document.title}")
        print(f"📏 File Size: {document.file_size:,} bytes")
        print(f"🔤 Content Length: {len(document.raw_content):,} → {len(document.clean_content):,} chars (after cleaning)")
        print(f"📚 Text Chunks: {len(document.textChunks)}")

        # Processing decision
        token_estimate = document.estimate_token_count()
        processing_strategy = "Document-level" if document.should_use_document_level_kg() else "Chunk-level"
        print(f"🔢 Token Estimate: {token_estimate:,}")
        print(f"🎯 Processing Strategy: {processing_strategy}")

        # Knowledge Graph results
        if document.is_kg_extracted and document.knowledge_graph:
            kg = document.knowledge_graph
            entities = kg.get('entities', set())
            relations = kg.get('relations', [])

            print(f"\n🧠 KNOWLEDGE GRAPH EXTRACTION")
            print(f"🏷️  Entities Extracted: {len(entities)}")
            print(f"🔗 Relations Extracted: {len(relations)}")

            # Show entities
            if entities:
                print(f"\n📝 Entities:")
                for i, entity in enumerate(sorted(list(entities)[:15]), 1):  # Show first 15
                    print(f"   {i:2d}. {entity}")
                if len(entities) > 15:
                    print(f"   ... and {len(entities) - 15} more")

            # Show relations
            if relations:
                print(f"\n🔗 Relations:")
                for i, rel in enumerate(relations[:10], 1):  # Show first 10
                    if isinstance(rel, tuple) and len(rel) >= 3:
                        print(f"   {i:2d}. {rel[0]} --[{rel[1]}]--> {rel[2]}")
                    else:
                        print(f"   {i:2d}. {rel}")
                if len(relations) > 10:
                    print(f"   ... and {len(relations) - 10} more")

        # Metadata
        print(f"\n🏷️  METADATA")
        print(f"Tags: {document.metadata.tags}")
        print(f"Categories: {document.metadata.categories}")
        print(f"Word Count: {document.metadata.word_count:,}")
        print(f"Section Headers: {len(document.metadata.section_headers)}")

        # Processing flags
        print(f"\n✅ PROCESSING STATUS")
        statuses = [
            ("Parsed", document.is_parsed),
            ("Cleaned", document.is_preprocessed),
            ("Chunked", document.is_chunked),
            ("Metadata Generated", document.is_metadata_generated),
            ("KG Extracted", document.is_kg_extracted)
        ]

        for status_name, status_value in statuses:
            icon = "✅" if status_value else "❌"
            print(f"{icon} {status_name}")

        # Save to JSON Knowledge Store
        print(f"\n💾 SAVING TO JSON KNOWLEDGE STORE")
        if document.is_kg_extracted and document.knowledge_graph:
            try:
                # Prepare document metadata for the knowledge store
                doc_metadata = {
                    "title": document.title,
                    "file_path": document_path,
                    "file_type": document.file_type,
                    "file_size": document.file_size,
                    "word_count": document.metadata.word_count,
                    "processing_strategy": "Document-level" if document.should_use_document_level_kg() else "Chunk-level",
                    "token_estimate": document.estimate_token_count(),
                    "tags": document.metadata.tags,
                    "categories": document.metadata.categories
                }

                # Save knowledge graph to JSON store
                success = json_store.save_knowledge_graph(
                    document_id=doc_id,
                    kg_data=document.knowledge_graph,
                    document_metadata=doc_metadata
                )

                if success:
                    print("✅ Knowledge graph saved to JSON store")

                    # Show knowledge store statistics
                    stats = json_store.get_stats()
                    print(f"📊 Knowledge Store Stats:")
                    print(f"   📝 Total Facts: {stats['total_facts']}")
                    print(f"   🏷️  Total Entities: {stats['total_entities']}")
                    print(f"   🔗 Total Relationships: {stats['total_relationships']}")
                    print(f"   📚 Unique Documents: {stats['unique_documents']}")
                else:
                    print("❌ Failed to save to JSON knowledge store")

            except Exception as e:
                print(f"❌ Error saving to JSON knowledge store: {e}")
        else:
            print("⚠️  No knowledge graph data to save")

        print("\n" + "="*50)
        print("🎉 Document processing complete!")
        print("="*50)

        # Optional: Save results to file
        output_file = f"{doc_id}_results.txt"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"Knowledge Graph Extraction Results\n")
            f.write(f"Document: {document.title}\n")
            f.write(f"Processed: {document.kg_extracted_at}\n\n")

            f.write(f"Entities ({len(entities)}):\n")
            for entity in sorted(list(entities)):
                f.write(f"- {entity}\n")

            f.write(f"\nRelations ({len(relations)}):\n")
            for rel in relations:
                if isinstance(rel, tuple) and len(rel) >= 3:
                    f.write(f"- {rel[0]} --[{rel[1]}]--> {rel[2]}\n")
                else:
                    f.write(f"- {rel}\n")

        print(f"💾 Results saved to: {output_file}")

    except Exception as e:
        logging.error(f"Document processing error: {e}")
        print(f"❌ Error processing document: {e}")
        raise


async def clear_knowledge_store():
    """Clear all data from the JSON knowledge store."""
    try:
        print("🗑️  Clearing knowledge store...")

        # Initialize JSON Knowledge Store
        json_store = JsonKnowledgeStore()

        # Get current stats before clearing
        stats = json_store.get_stats()
        print(f"📊 Current store contains:")
        print(f"   📝 Facts: {stats['total_facts']}")
        print(f"   🏷️  Entities: {stats['total_entities']}")
        print(f"   🔗 Relationships: {stats['total_relationships']}")
        print(f"   📚 Documents: {stats['unique_documents']}")

        # Clear all data
        json_store.data = {"facts": [], "entities": [], "relationships": [], "metadata": {}}
        json_store._update_metadata()
        json_store._save_data()

        print("\n✅ Knowledge store cleared successfully!")
        print("📊 Store is now empty and ready for new data.")

    except Exception as e:
        logging.error(f"Knowledge store clear error: {e}")
        print(f"❌ Error clearing knowledge store: {e}")
        raise


async def query_knowledge_store(query: str):
    """Query the JSON knowledge store."""
    try:
        print(f"🔍 Querying knowledge store: '{query}'")

        # Initialize JSON Knowledge Store
        json_store = JsonKnowledgeStore()

        print("\n" + "="*50)
        print("📊 KNOWLEDGE STORE QUERY RESULTS")
        print("="*50)

        # Search entities
        entities = json_store.search_entities(query)
        print(f"\n🏷️  ENTITIES FOUND: {len(entities)}")
        for i, entity in enumerate(entities[:10], 1):  # Show first 10
            print(f"   {i:2d}. {entity['name']} (type: {entity['type']})")
            print(f"       Documents: {len(entity.get('document_ids', []))}")
            print(f"       Created: {entity.get('created_at', 'Unknown')}")

        if len(entities) > 10:
            print(f"       ... and {len(entities) - 10} more")

        # Search relationships
        relationships = json_store.search_relationships(query)
        print(f"\n🔗 RELATIONSHIPS FOUND: {len(relationships)}")
        for i, rel in enumerate(relationships[:10], 1):  # Show first 10
            print(f"   {i:2d}. {rel['source_entity']} --[{rel['relation_type']}]--> {rel['target_entity']}")
            print(f"       Documents: {len(rel.get('document_ids', []))}")
            print(f"       Created: {rel.get('created_at', 'Unknown')}")

        if len(relationships) > 10:
            print(f"       ... and {len(relationships) - 10} more")

        # Search facts
        facts = json_store.search_facts(query)
        print(f"\n📝 FACTS FOUND: {len(facts)}")
        for i, fact in enumerate(facts[:5], 1):  # Show first 5
            print(f"   {i:2d}. {fact['content'][:100]}{'...' if len(fact['content']) > 100 else ''}")
            print(f"       Category: {fact.get('category', 'general')}")
            print(f"       Tags: {', '.join(fact.get('tags', []))}")

        if len(facts) > 5:
            print(f"       ... and {len(facts) - 5} more")

        # Show overall statistics
        stats = json_store.get_stats()
        print(f"\n📊 OVERALL STATISTICS")
        print(f"📝 Total Facts: {stats['total_facts']}")
        print(f"🏷️  Total Entities: {stats['total_entities']}")
        print(f"🔗 Total Relationships: {stats['total_relationships']}")
        print(f"📚 Unique Documents: {stats['unique_documents']}")
        print(f"🕐 Last Updated: {stats.get('last_updated', 'Unknown')}")

        print("\n" + "="*50)
        print("🎉 Query complete!")
        print("="*50)

    except Exception as e:
        logging.error(f"Knowledge store query error: {e}")
        print(f"❌ Error querying knowledge store: {e}")
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
            print("❌ Error: Please provide a document path")
            print("Usage: python src/main.py process <document_path>")
        elif command == "query" and len(sys.argv) > 2:
            query = " ".join(sys.argv[2:])  # Join all remaining args as query
            await query_knowledge_store(query)
        elif command == "query":
            print("❌ Error: Please provide a query")
            print("Usage: python src/main.py query <search_terms>")
        elif command == "clear_kg_store":
            await clear_knowledge_store()
        else:
            print(f"❌ Unknown command: {command}")
            print_usage()
    else:
        print_usage()


def print_usage():
    """Print usage information."""
    print("🤖 AI Module - Usage:")
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
    print("📝 LLM Provider Configuration:")
    print("  export KG_LLM_PROVIDER=mock      # Use mock extraction (default, no LLM required)")
    print("  export KG_LLM_PROVIDER=ollama    # Use local Ollama (requires Ollama installed)")
    print("  export KG_LLM_PROVIDER=openai    # Use OpenAI API (requires OPENAI_API_KEY)")
    print("")
    print("🚀 Full Example with OpenAI:")
    print('  export OPENAI_API_KEY="your-api-key"')
    print('  export KG_LLM_PROVIDER=openai')
    print('  python src/main.py process "/path/to/document.md"')
    print("")
    print("💾 Knowledge Store Features:")
    print("  • Automatically saves extracted entities and relationships to JSON store")
    print("  • Deduplicates entities across multiple documents")
    print("  • Tracks document sources for each entity/relationship")
    print("  • Provides full-text search across facts, entities, and relationships")
    print("")
    print("Supported formats: .md, .txt, .pdf (and more)")
    print("The system will automatically:")
    print("  ✓ Clean and parse the document")
    print("  ✓ Extract entities and relationships")
    print("  ✓ Generate metadata and topics")
    print("  ✓ Save to JSON knowledge store")
    print("  ✓ Save results to a file")


if __name__ == "__main__":
    asyncio.run(main())