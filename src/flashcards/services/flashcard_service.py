"""Improved flashcard service with better separation of concerns"""

from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from ..config import FlashcardConfig

from ..models import Card, Deck, FlashcardReview
from .card_service import CardService
from .deck_service import DeckService  
from .review_service import ReviewService
from .repositories import CardRepository, DeckRepository, ReviewRepository
from .anki_service import AnkiService


class Result:
    """Result wrapper for consistent error handling"""
    
    def __init__(self, success: bool, data: Any = None, error: str = None):
        self.success = success
        self.data = data
        self.error = error
    
    @classmethod
    def success(cls, data: Any = None):
        return cls(True, data)
    
    @classmethod
    def failure(cls, error: str):
        return cls(False, error=error)


class FlashcardOrchestrator:
    """
    Orchestrates flashcard operations
    
    Coordinates between services but doesn't implement business logic.
    This follows the Facade pattern - provides a simple interface to complex subsystems.
    """
    
    def __init__(self, 
                 card_service: CardService,
                 deck_service: DeckService,
                 review_service: ReviewService,
                 anki_service: Optional[AnkiService] = None):
        self.card_service = card_service
        self.deck_service = deck_service
        self.review_service = review_service
        self.anki_service = anki_service
        self.logger = logging.getLogger(__name__)
    
    # === CARD OPERATIONS ===
    
    def create_card(self, user_id: str, front: str, back: str, 
                   domains: List[str] = None, algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM) -> Result:
        """Create a new flashcard"""
        try:
            card = self.card_service.create_card(user_id, front, back, domains, algorithm)
            
            # Optional: Sync to Anki in background
            if self.anki_service:
                self.anki_service.sync_card_async(card)
            
            return Result.success(card)
        except Exception as e:
            self.logger.error(f"Failed to create card: {e}")
            return Result.failure(str(e))
    
    def get_card(self, card_id: str) -> Result:
        """Get card by ID"""
        try:
            card = self.card_service.get_card(card_id)
            if card:
                return Result.success(card)
            return Result.failure("Card not found")
        except Exception as e:
            return Result.failure(str(e))
    
    def review_card(self, card_id: str, quality: int, 
                   response_time: Optional[float] = None) -> Result:
        """Process a card review"""
        try:
            # Get card
            card_result = self.get_card(card_id)
            if not card_result.success:
                return card_result
            
            card = card_result.data
            
            # Process review
            review = self.review_service.process_review(card, quality, response_time)
            
            # Save updated card
            self.card_service.update_card(card)
            
            return Result.success(review)
        except Exception as e:
            self.logger.error(f"Failed to review card: {e}")
            return Result.failure(str(e))
    
    def get_due_cards(self, user_id: str, limit: Optional[int] = None) -> Result:
        """Get cards due for review"""
        try:
            cards = self.card_service.get_due_cards(user_id, limit)
            return Result.success(cards)
        except Exception as e:
            return Result.failure(str(e))
    
    # === DECK OPERATIONS ===
    
    def create_deck(self, user_id: str, name: str, description: str = "", 
                   algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM) -> Result:
        """Create a new deck"""
        try:
            deck = self.deck_service.create_deck(user_id, name, description, algorithm)
            
            # Optional: Create Anki deck
            if self.anki_service:
                self.anki_service.create_deck_async(deck)
            
            return Result.success(deck)
        except Exception as e:
            self.logger.error(f"Failed to create deck: {e}")
            return Result.failure(str(e))
    
    def get_user_decks(self, user_id: str) -> Result:
        """Get all decks for user"""
        try:
            decks = self.deck_service.get_user_decks(user_id)
            return Result.success(decks)
        except Exception as e:
            return Result.failure(str(e))
    
    # === STATISTICS ===
    
    def get_user_stats(self, user_id: str) -> Result:
        """Get user statistics"""
        try:
            cards = self.card_service.get_user_cards(user_id)
            due_cards = self.card_service.get_due_cards(user_id)
            
            stats = {
                'total_cards': len(cards),
                'cards_due': len(due_cards),
                'cards_reviewed_today': len([
                    c for c in cards 
                    if c.reviewed_at.date() == datetime.now().date()
                ]),
                'average_ease_factor': (
                    sum(c.scheduling.ease_factor for c in cards) / len(cards) 
                    if cards else 0
                )
            }
            
            return Result.success(stats)
        except Exception as e:
            return Result.failure(str(e))
    
    # === ANKI SYNC ===
    
    def sync_with_anki(self, user_id: str) -> Result:
        """Sync user's flashcards with Anki"""
        if not self.anki_service:
            return Result.failure("Anki service not available")
        
        try:
            cards = self.card_service.get_user_cards(user_id)
            sync_result = self.anki_service.sync_cards(cards)
            return Result.success(sync_result)
        except Exception as e:
            return Result.failure(str(e))


def create_flashcard_orchestrator(db_path: str = FlashcardConfig.DATABASE_PATH, 
                                enable_anki: bool = FlashcardConfig.ANKI_SYNC_ENABLED_DEFAULT) -> FlashcardOrchestrator:
    """Factory function to create properly configured orchestrator"""
    
    # Import here to avoid circular dependencies
    from .json_db import JSONFlashcardDB
    from .repositories import JSONCardRepository, JSONDeckRepository, JSONReviewRepository
    
    # Create database
    db = JSONFlashcardDB(db_path)
    
    # Create repositories
    card_repo = JSONCardRepository(db)
    deck_repo = JSONDeckRepository(db)
    review_repo = JSONReviewRepository(db)
    
    # Create services
    card_service = CardService(card_repo)
    deck_service = DeckService(deck_repo)
    review_service = ReviewService()
    
    # Optional Anki service
    anki_service = None
    if enable_anki:
        try:
            from .anki_service import AnkiService
            anki_service = AnkiService()
        except ImportError:
            pass
    
    return FlashcardOrchestrator(
        card_service=card_service,
        deck_service=deck_service,
        review_service=review_service,
        anki_service=anki_service
    )
