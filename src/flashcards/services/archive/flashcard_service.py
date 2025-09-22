"""Main flashcard service - your primary interface for flashcard operations"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
from pathlib import Path

from ..models.Card import Card
from ..models import Deck, FlashcardReview
from ..algorithms import get_algorithm, ALGORITHMS
from .json_db import JSONFlashcardDB
from .anki_connect import AnkiConnectClient, create_anki_client
from .review_service import ReviewService


class FlashcardService:
    """
    Main service for all flashcard operations

    This is your primary interface - import this into your main file.
    Handles all flashcard CRUD, reviews, scheduling, and Anki sync.
    """

    def __init__(self, db_path: str = "database/flashcards", enable_anki: bool = True):
        self.db = JSONFlashcardDB(db_path)
        self.review_service = ReviewService()  # Handle algorithm logic
        self.logger = logging.getLogger(__name__)

        # Anki integration
        self.anki_enabled = enable_anki
        self.anki_client = None
        if enable_anki:
            try:
                self.anki_client = create_anki_client()
                self.anki_available = self.anki_client.test_connection()
            except Exception as e:
                self.logger.warning(f"Anki integration disabled: {e}")
                self.anki_available = False
        else:
            self.anki_available = False

        self.logger.info(f"FlashcardService initialized (Anki: {'enabled' if self.anki_available else 'disabled'})")

    # === DECK OPERATIONS ===

    def create_deck(self, user_id: str, name: str, description: str = "",
                   algorithm: str = "sm2") -> Optional[Deck]:
        """Create a new deck"""
        try:
            deck = Deck.create_new(user_id, name, description, algorithm)

            if self.db.create_deck(deck.to_dict()):
                self.logger.info(f"Created deck '{name}' for user {user_id}")

                # Create in Anki if available
                if self.anki_available and self.anki_client:
                    anki_deck_name = f"Telegram_{name}"
                    if self.anki_client.create_deck(anki_deck_name):
                        deck.anki_deck_name = anki_deck_name
                        self.db.update_deck(deck.deck_id, deck.to_dict())

                return deck
            return None
        except Exception as e:
            self.logger.error(f"Failed to create deck: {e}")
            return None

    def get_deck(self, deck_id: str) -> Optional[Deck]:
        """Get deck by ID"""
        deck_data = self.db.get_deck(deck_id)
        if deck_data:
            return Deck.from_dict(deck_data)
        return None

    def get_user_decks(self, user_id: str) -> List[Deck]:
        """Get all decks for a user"""
        deck_data_list = self.db.get_user_decks(user_id)
        return [Deck.from_dict(deck_data) for deck_data in deck_data_list]

    def update_deck(self, deck: Deck) -> bool:
        """Update deck"""
        return self.db.update_deck(deck.deck_id, deck.to_dict())

    def delete_deck(self, deck_id: str) -> bool:
        """Delete deck and all its cards"""
        return self.db.delete_deck(deck_id)

    # === CARD OPERATIONS ===

    def create_card(self, user_id: str, front: str, back: str, 
                   domains: List[str] = None, algorithm: str = "sm2") -> Optional[Card]:
        """Create a new flashcard"""
        try:
            card = Card.create_new(user_id, front, back, domains, algorithm)
            
            if self.db.create_card(card.to_dict()):
                self.logger.info(f"Created card {card.id}")
                return card
            return None
        except Exception as e:
            self.logger.error(f"Failed to create card: {e}")
            return None

    def get_card(self, card_id: str) -> Optional[Card]:
        """Get card by ID"""
        card_data = self.db.get_card(card_id)
        if card_data:
            return Card.from_dict(card_data)
        return None

    def update_card(self, card: Card) -> bool:
        """Update card"""
        return self.db.update_card(card.id, card.to_dict())

    def delete_card(self, card_id: str) -> bool:
        """Delete card"""
        return self.db.delete_card(card_id)

    def get_deck_cards(self, deck_id: str) -> List[Card]:
        """Get all cards in a deck"""
        card_data_list = self.db.get_deck_cards(deck_id)
        return [Card.from_dict(card_data) for card_data in card_data_list]

    def get_user_cards(self, user_id: str) -> List[Card]:
        """Get all cards for a user"""
        card_data_list = self.db.get_user_cards(user_id)
        return [Card.from_dict(card_data) for card_data in card_data_list]

    # === REVIEW OPERATIONS ===

    def get_due_cards(self, user_id: str, limit: Optional[int] = None) -> List[Card]:
        """Get cards due for review"""
        card_data_list = self.db.get_due_cards(user_id)
        cards = [Card.from_dict(card_data) for card_data in card_data_list]

        # Filter for actually due cards and sort by priority
        due_cards = [c for c in cards if c.is_due()]
        due_cards.sort(key=lambda c: c.scheduling.interval_days)  # Shorter intervals first

        return due_cards[:limit] if limit else due_cards

    def review_card(self, card_id: str, quality: int, response_time: Optional[float] = None,
                   **kwargs) -> Optional[FlashcardReview]:
        """Process a card review"""
        try:
            card = self.get_card(card_id)
            if not card:
                return None

            # ReviewService handles the algorithm logic
            review = self.review_service.process_review(card, quality, response_time, **kwargs)

            # Save changes (card was updated by review service)
            self.db.update_card(card.id, card.to_dict())
            self.db.save_review(review.to_dict())

            return review
        except Exception as e:
            self.logger.error(f"Failed to review card {card_id}: {e}")
            return None

    def sync_card_to_anki(self, card: Card) -> bool:
        """Sync a single card to Anki (separate from core operations)"""
        if not self.anki_available or not self.anki_client:
            return False
            
        try:
            # Create Anki note if not already synced
            if not card.anki_note_id:
                anki_note_id = self.anki_client.add_note("Default", card.front, card.back)
                if anki_note_id:
                    card.anki_note_id = anki_note_id
                    self.update_card(card)
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to sync card to Anki: {e}")
            return False

    def get_card_reviews(self, card_id: str) -> List[FlashcardReview]:
        """Get all reviews for a card"""
        review_data_list = self.db.get_card_reviews(card_id)
        return [FlashcardReview.from_dict(review_data) for review_data in review_data_list]

    # === ALGORITHM OPERATIONS ===
    def switch_card_algorithm(self, card_id: str, new_algorithm: str) -> bool:
        """Switch a card to use different algorithm"""
        try:
            card = self.get_card(card_id)
            if not card:
                return False

            card.switch_algorithm(new_algorithm)
            return self.update_card(card)
        except Exception as e:
            self.logger.error(f"Failed to switch algorithm for card {card_id}: {e}")
            return False

    def switch_deck_algorithm(self, deck_id: str, new_algorithm: str) -> bool:
        """Switch deck's default algorithm"""
        try:
            deck = self.get_deck(deck_id)
            if not deck:
                return False

            deck.switch_default_algorithm(new_algorithm)
            return self.update_deck(deck)
        except Exception as e:
            self.logger.error(f"Failed to switch algorithm for deck {deck_id}: {e}")
            return False

    def get_available_algorithms(self) -> Dict[str, Dict[str, Any]]:
        """Get information about all available algorithms"""
        algorithms_info = {}
        for name, algo_class in ALGORITHMS.items():
            algo = algo_class()
            algorithms_info[name] = algo.get_algorithm_info()
        return algorithms_info

    # === STATISTICS ===

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get user statistics"""
        cards = self.get_user_cards(user_id)
        due_cards = self.get_due_cards(user_id)

        return {
            'total_cards': len(cards),
            'cards_due': len(due_cards),
            'cards_reviewed_today': len([c for c in cards if c.reviewed_at.date() == datetime.now().date()]),
            'average_ease_factor': sum(c.scheduling.ease_factor for c in cards) / len(cards) if cards else 0
        }

    def get_deck_stats(self, deck_id: str) -> Dict[str, Any]:
        """Get deck statistics"""
        cards = self.get_deck_cards(deck_id)
        deck = self.get_deck(deck_id)

        if not deck:
            return {}

        due_cards = [c for c in cards if c.is_due()]

        return {
            'deck_id': deck_id,
            'name': deck.name,
            'total_cards': len(cards),
            'cards_due': len(due_cards),
            'created_at': deck.created_at.isoformat()
        }

    # === ANKI SYNC ===

    def sync_with_anki(self, user_id: str) -> Dict[str, Any]:
        """Sync user's flashcards with Anki"""
        if not self.anki_available:
            return {'success': False, 'error': 'Anki not available'}

        try:
            cards = self.get_user_cards(user_id)
            synced_count = 0
            
            for card in cards:
                if self.sync_card_to_anki(card):
                    synced_count += 1

            return {'success': True, 'synced_cards': synced_count}
        except Exception as e:
            self.logger.error(f"Anki sync failed: {e}")
            return {'success': False, 'error': str(e)}

    # === UTILITIES ===

    def backup_database(self, backup_path: str) -> bool:
        """Create database backup"""
        return self.db.backup_database(backup_path)

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        return {
            'anki_available': self.anki_available,
            'algorithms_available': list(ALGORITHMS.keys())
        }

    def close(self):
        """Clean up resources"""
        self.logger.info("FlashcardService closed")


def create_flashcard_service(db_path: str = None, enable_anki: bool = True) -> FlashcardService:
    """Factory function to create FlashcardService"""
    if db_path is None:
        # Default to project database directory
        db_path = "database/flashcards"

    return FlashcardService(db_path, enable_anki)