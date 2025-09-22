"""Example: How to use improved flashcard service in main.py"""

import asyncio
import logging
from pathlib import Path

# Your improved flashcard service
from flashcards.services.improved_flashcard_service import create_flashcard_orchestrator
from knowledge_graph import create_json_client


class AIModuleApp:
    def __init__(self):
        # Create services
        self.kg_client = create_json_client()
        self.flashcard_orchestrator = create_flashcard_orchestrator(
            db_path="database/flashcards",
            enable_anki=True
        )
        self.logger = logging.getLogger(__name__)

    async def process_document_with_flashcards(self, document_path: str, user_id: str, 
                                              generate_flashcards: bool = True):
        """Process document and optionally generate flashcards"""
        
        # 1. Process document with knowledge graph (your existing logic)
        doc_result = self.kg_client.add_document(
            document_path=document_path,
            document_id=f"doc_{user_id}_{int(time.time())}",
            document_type=None
        )
        
        if not doc_result:
            return {"success": False, "error": "Failed to process document"}
        
        # 2. Extract entities from document
        entities = self.kg_client.extract_document_ontology(doc_result)
        
        # 3. Generate flashcards if requested
        flashcards_created = []
        if generate_flashcards:
            # Create a deck for this document
            deck_name = Path(document_path).stem
            deck_result = self.flashcard_orchestrator.create_deck(
                user_id=user_id,
                name=f"Document: {deck_name}",
                description=f"Flashcards from {document_path}",
                algorithm="sm2"
            )
            
            if deck_result.success:
                deck = deck_result.data
                
                # Generate flashcards from entities
                for entity in entities[:10]:  # Limit to 10 cards
                    card_result = self.flashcard_orchestrator.create_card(
                        user_id=user_id,
                        front=f"What is {entity.name}?",
                        back=entity.description or f"A {entity.type} mentioned in the document",
                        domains=[entity.type, "document_knowledge"],
                        algorithm="sm2"
                    )
                    
                    if card_result.success:
                        flashcards_created.append(card_result.data)
                        self.logger.info(f"Created flashcard for entity: {entity.name}")
                    else:
                        self.logger.error(f"Failed to create flashcard: {card_result.error}")
        
        return {
            "success": True,
            "document_processed": doc_result,
            "flashcards_created": len(flashcards_created),
            "flashcards": flashcards_created
        }

    async def get_user_study_session(self, user_id: str, max_cards: int = 5):
        """Get cards for user study session"""
        
        # Get due cards
        due_result = self.flashcard_orchestrator.get_due_cards(user_id, limit=max_cards)
        
        if not due_result.success:
            return {"success": False, "error": due_result.error}
        
        due_cards = due_result.data
        
        # Get user stats
        stats_result = self.flashcard_orchestrator.get_user_stats(user_id)
        stats = stats_result.data if stats_result.success else {}
        
        return {
            "success": True,
            "cards": due_cards,
            "session_info": {
                "cards_in_session": len(due_cards),
                "total_cards": stats.get("total_cards", 0),
                "cards_due": stats.get("cards_due", 0)
            }
        }

    async def process_card_review(self, user_id: str, card_id: str, quality: int, 
                                response_time_seconds: float = None):
        """Process a single card review"""
        
        review_result = self.flashcard_orchestrator.review_card(
            card_id=card_id,
            quality=quality,
            response_time=response_time_seconds
        )
        
        if review_result.success:
            review = review_result.data
            self.logger.info(f"User {user_id} reviewed card {card_id} with quality {quality}")
            
            return {
                "success": True,
                "review": review,
                "next_review_date": review_result.data  # When to review next
            }
        else:
            return {"success": False, "error": review_result.error}


# Usage in your main.py
async def main():
    app = AIModuleApp()
    
    # Example: Process document and create flashcards
    result = await app.process_document_with_flashcards(
        document_path="data/machine_learning_notes.pdf",
        user_id="user123",
        generate_flashcards=True
    )
    
    print(f"Document processed: {result['success']}")
    print(f"Flashcards created: {result['flashcards_created']}")
    
    # Example: Get study session for user
    session = await app.get_user_study_session("user123", max_cards=5)
    print(f"Study session ready: {len(session['cards'])} cards")


if __name__ == "__main__":
    asyncio.run(main())
