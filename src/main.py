#!/usr/bin/env python3
"""
Main entry point for the AI Module application.
"""
import asyncio
import logging
import sys
import os
from typing import Optional
import signal
import threading
import time
import sys
from pathlib import Path

# IMPORTANT: Setup DSPy cache before any DSPy imports to avoid permission errors
def setup_dspy_cache():
    """Setup DSPy cache directory to avoid permission errors"""
    try:
        # Option 1: Use project-local cache
        project_root = Path(__file__).parent.parent  # Go up from src/ to project root
        cache_dir = project_root / '.cache' / 'dspy'
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ['DSPY_CACHEDIR_ROOT'] = str(cache_dir)
        logging.info(f"DSPy cache directory set to: {cache_dir}")
        
    except Exception as e:
        # Option 2: Use user home cache
        try:
            home_cache = Path.home() / '.cache' / 'dspy'
            home_cache.mkdir(parents=True, exist_ok=True)
            os.environ['DSPY_CACHEDIR_ROOT'] = str(home_cache)
            logging.info(f"Using home cache directory: {home_cache}")
            
        except Exception as e2:
            # Option 3: Disable caching entirely
            os.environ['DSPY_CACHE_DISABLED'] = '1'
            logging.warning("Could not create cache directory, disabled DSPy caching")

# Setup DSPy cache before any imports
setup_dspy_cache()

# Add the src directory to Python path
current_dir = Path(__file__).parent  # src/
sys.path.insert(0, str(current_dir))

from bots import get_telegram_bot
from knowledge_graph import create_json_client, KnowledgeGraphClient
from flashcards import create_flashcard_client
from web import run_web_server
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


async def test_flashcards():
    """Test the flashcard system."""
    logger = logging.getLogger(__name__)

    try:
        logger.info("🧪 Testing Flashcard System (New API)")
        logger.info("=" * 50)

        # 1. Initialize client
        logger.info("1. Initializing FlashcardClient...")
        client = create_flashcard_client(enable_anki=False)

        # 2. Test health check
        logger.info("2. Health Check:")
        health = client.health_check()
        if health.success:
            logger.info(f"   ✅ System healthy")
            logger.info(f"   Version: {health.data['version']}")
            logger.info(f"   Anki: {health.data['services']['anki_integration']}")
        else:
            logger.error(f"   ❌ Health check failed: {health.error}")
            return

        # 3. Create a user and deck
        user_id = "test_user_123"
        logger.info(f"3. Creating deck for user {user_id}...")

        deck_result = client.create_deck(
            user_id=user_id,
            name="Python Basics",
            description="Learning Python fundamentals",
            algorithm="sm2"
        )

        if deck_result.success:
            deck_data = deck_result.data
            logger.info(f"   ✅ Created deck: '{deck_data['name']}' (ID: {deck_data['id'][:8]}...)")
            logger.info(f"   Algorithm: {deck_data['default_algorithm']}")
        else:
            logger.error(f"   ❌ Failed to create deck: {deck_result.error}")
            return

        # 4. Create some flashcards
        logger.info("4. Creating flashcards...")

        cards_data = [
            ("What is a Python list?", "An ordered, mutable collection: [1, 2, 3]"),
            ("How do you define a function in Python?", "def function_name(parameters): return value"),
            ("What is a dictionary in Python?", "A key-value collection: {'key': 'value'}"),
            ("How do you create a for loop?", "for item in iterable: print(item)")
        ]

        created_cards = []
        for front, back in cards_data:
            card_result = client.create_card(
                user_id=user_id,
                front=front,
                back=back,
                domains=["python", "basics"]  # Using domains instead of tags
            )
            if card_result.success:
                created_cards.append(card_result.data)
                logger.info(f"   ✅ Created card: {front[:30]}...")
            else:
                logger.error(f"   ❌ Failed to create card: {card_result.error}")

        logger.info(f"   Created {len(created_cards)} cards")

        # 5. Check due cards
        logger.info("5. Checking due cards...")
        due_cards_result = client.get_due_cards(user_id)
        if due_cards_result.success:
            due_cards = due_cards_result.data
            logger.info(f"   Cards due for review: {len(due_cards)}")
        else:
            logger.error(f"   ❌ Failed to get due cards: {due_cards_result.error}")
            due_cards = []

        # 6. Review a card
        logger.info("6. Reviewing cards...")
        if due_cards:
            card_to_review = due_cards[0]
            logger.info(f"   Reviewing: {card_to_review['front']}")
            logger.info(f"   Algorithm: {card_to_review.get('algorithm', 'sm2')}")

            # Review with quality 4 (good recall)
            review_result = client.review_card(card_to_review['id'], quality=4, user_id=user_id)

            if review_result.success:
                logger.info(f"   ✅ Review completed!")
                review_data = review_result.data
                logger.info(f"   Next review: {review_data['next_review_date']}")
                
                # Get updated card info
                updated_card_result = client.get_card(card_to_review['id'])
                if updated_card_result.success:
                    updated_card = updated_card_result.data
                    logger.info(f"   Ease factor: {updated_card['scheduling']['ease_factor']:.2f}")
                    logger.info(f"   Interval: {updated_card['scheduling']['interval_days']} days")
            else:
                logger.error(f"   ❌ Review failed: {review_result.error}")

        # 7. Start a study session
        logger.info("7. Starting study session...")
        session_result = client.start_study_session(user_id, max_cards=3)
        if session_result.success:
            session_data = session_result.data
            logger.info(f"   ✅ Session started with {len(session_data['cards'])} cards")
            logger.info(f"   Session ID: {session_data['session_id']}")
        else:
            logger.error(f"   ❌ Failed to start session: {session_result.error}")

        # 8. Get statistics
        logger.info("8. User Statistics:")
        stats_result = client.get_user_stats(user_id)
        if stats_result.success:
            stats = stats_result.data
            logger.info(f"   Total cards: {stats['total_cards']}")
            logger.info(f"   Cards due: {stats['cards_due']}")
            logger.info(f"   Reviewed today: {stats['cards_reviewed_today']}")
            logger.info(f"   Average ease factor: {stats['average_ease_factor']:.2f}")
        else:
            logger.error(f"   ❌ Failed to get stats: {stats_result.error}")

        # 9. Get user decks
        logger.info("9. User Decks:")
        decks_result = client.get_user_decks(user_id)
        if decks_result.success:
            decks = decks_result.data
            for deck in decks:
                logger.info(f"   📚 {deck['name']} (Algorithm: {deck['default_algorithm']})")
        else:
            logger.error(f"   ❌ Failed to get decks: {decks_result.error}")

        logger.info("=" * 50)
        logger.info("🎉 Flashcard system test completed!")
        logger.info("Check the database/ folder for created JSON files")

    except Exception as e:
        logger.error(f"Flashcard test error: {e}")
        raise


class UnifiedApplication:
    """Unified application that runs web server, telegram bot, and backend services"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.running = False
        self.tasks = []

    async def run_all_services(self, host: str = "127.0.0.1", port: int = 8001):
        """Run web server, telegram bot, and all backend services"""
        self.logger.info("Starting Unified AI Module Application")
        self.logger.info("=" * 60)

        # Load environment variables
        dotenv.load_dotenv()

        self.running = True

        try:
            # Create tasks for all services
            tasks = []

            # 1. Web server task
            self.logger.info(f"Starting Web Server at http://{host}:{port}")
            web_task = asyncio.create_task(run_web_server(host, port))
            tasks.append(("web_server", web_task))

            # 2. Telegram bot task (if configured)
            if os.getenv("TELEGRAM_BOT_TOKEN"):
                self.logger.info("Starting Telegram Bot")
                telegram_task = asyncio.create_task(self.run_telegram_bot_service())
                tasks.append(("telegram_bot", telegram_task))
            else:
                self.logger.warning("Telegram bot not configured (missing TELEGRAM_BOT_TOKEN)")

            self.tasks = tasks

            # Print startup info
            self.logger.info("All services starting...")
            self.logger.info("=" * 60)
            self.logger.info("ACCESS POINTS:")
            self.logger.info(f"   • Web Interface: http://{host}:{port}")
            self.logger.info(f"   • API Documentation: http://{host}:{port}/docs")
            self.logger.info(f"   • Knowledge Graph Data: http://{host}:{port}/database/knowledge_store.json")
            if os.getenv("TELEGRAM_BOT_TOKEN"):
                self.logger.info(f"   • Telegram Bot: Active (check your Telegram app)")
            self.logger.info("=" * 60)
            self.logger.info("UPLOAD DOCUMENTS:")
            self.logger.info("   • Visit the web interface and click 'Upload Document'")
            self.logger.info("   • Add tags, select domain, and enable flashcard generation")
            self.logger.info("   • Documents will be processed and added to the knowledge graph")
            self.logger.info("=" * 60)
            self.logger.info("READY FOR USE!")
            self.logger.info("Press Ctrl+C to stop all services")

            # Wait for all tasks to complete (or until interrupted)
            await asyncio.gather(*[task for _, task in tasks], return_exceptions=True)

        except KeyboardInterrupt:
            self.logger.info("Received interrupt signal, stopping services...")
            await self.shutdown()
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            await self.shutdown()
            raise

    async def run_telegram_bot_service(self):
        """Run the telegram bot as a service"""
        try:
            TelegramBot = get_telegram_bot()
            bot = TelegramBot()
            await bot.run_forever()
        except Exception as e:
            self.logger.error(f"Telegram bot service error: {e}")
            raise

    async def shutdown(self):
        """Gracefully shutdown all services"""
        self.running = False

        self.logger.info("🔄 Shutting down services...")

        # Cancel all running tasks
        for service_name, task in self.tasks:
            if not task.done():
                self.logger.info(f"   Stopping {service_name}...")
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        self.logger.info("✅ All services stopped successfully")


async def run_unified_application(host: str = "127.0.0.1", port: int = 8001):
    """Run the unified application with all services"""
    app = UnifiedApplication()
    await app.run_all_services(host, port)


def print_usage():
    """Print usage information for the main application."""
    print("\nKnowledge Graph AI Module - Usage")
    print("=" * 50)
    print("Commands:")
    print("  python src/main.py                         # Run full application (default)")
    print("  python src/main.py app [port] [host]       # Run full application with custom port/host")
    print("  python src/main.py telegram                # Run only telegram bot")
    print("  python src/main.py process <document_path> # Process a document")
    print("  python src/main.py query <search_terms>    # Query knowledge store")
    print("  python src/main.py clear_kg_store          # Clear knowledge store")
    print("  python src/main.py test_flashcards         # Test flashcard system")
    print("\nOr from project root:")
    print("  uv run main.py                             # Run with uv (recommended)")
    print("\nWeb Interface will be available at: http://127.0.0.1:8001")
    print("=" * 50)


async def main():
    """Main application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "application" or command == "app":
            # Run unified application (default mode)
            host = "127.0.0.1"
            port = 8001

            # Check for custom host/port
            if len(sys.argv) > 2:
                try:
                    port = int(sys.argv[2])
                except ValueError:
                    logging.error(f"Invalid port: {sys.argv[2]}")
                    return
            if len(sys.argv) > 3:
                host = sys.argv[3]

            await run_unified_application(host, port)
        elif command == "telegram":
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
        elif command == "test_flashcards":
            await test_flashcards()
        else:
            logging.error(f"Unknown command: {command}")
            print_usage()
    else:
        # Default to unified application if no command provided
        await run_unified_application()



if __name__ == "__main__":
    asyncio.run(main())