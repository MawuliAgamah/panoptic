"""Main flashcard service - your primary interface for flashcard operations"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import logging
from pathlib import Path

from ..models import Flashcard, Deck, FlashcardReview
from ..algorithms import get_algorithm, ALGORITHMS
from .json_db import JSONFlashcardDB
from .anki_connect import AnkiConnectClient, create_anki_client


class FlashcardService:
    """
    Main service for all flashcard operations

    This is your primary interface - import this into your main file.
    Handles all flashcard CRUD, reviews, scheduling, and Anki sync.
    """

    def __init__(self, db_path: str = "database/flashcards", enable_anki: bool = True):
        self.db = JSONFlashcardDB(db_path)
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

    def create_card(self, deck_id: str, user_id: str, front: str, back: str,
                   tags: List[str] = None, algorithm: Optional[str] = None) -> Optional[Flashcard]:
        """Create a new flashcard"""
        try:
            # Get deck to use its default algorithm if none specified
            if algorithm is None:
                deck = self.get_deck(deck_id)
                algorithm = deck.default_algorithm if deck else "sm2"

            card = Flashcard.create_new(deck_id, user_id, front, back, tags, algorithm)

            if self.db.create_card(card.to_dict()):
                self.logger.info(f"Created card in deck {deck_id}")

                # Add to Anki if available
                if self.anki_available and self.anki_client:
                    deck = self.get_deck(deck_id)
                    if deck and deck.anki_deck_name:
                        anki_note_id = self.anki_client.add_note(deck.anki_deck_name, front, back)
                        if anki_note_id:
                            card.anki_note_id = anki_note_id
                            self.db.update_card(card.card_id, card.to_dict())

                return card
            return None
        except Exception as e:
            self.logger.error(f"Failed to create card: {e}")
            return None

    def get_card(self, card_id: str) -> Optional[Flashcard]:
        """Get card by ID"""
        card_data = self.db.get_card(card_id)
        if card_data:
            return Flashcard.from_dict(card_data)
        return None

    def update_card(self, card: Flashcard) -> bool:
        """Update card"""
        return self.db.update_card(card.card_id, card.to_dict())

    def delete_card(self, card_id: str) -> bool:
        """Delete card"""
        return self.db.delete_card(card_id)

    def get_deck_cards(self, deck_id: str) -> List[Flashcard]:
        """Get all cards in a deck"""
        card_data_list = self.db.get_deck_cards(deck_id)
        return [Flashcard.from_dict(card_data) for card_data in card_data_list]

    def get_user_cards(self, user_id: str) -> List[Flashcard]:
        """Get all cards for a user"""
        card_data_list = self.db.get_user_cards(user_id)
        return [Flashcard.from_dict(card_data) for card_data in card_data_list]

    # === REVIEW OPERATIONS ===

    def get_due_cards(self, user_id: str, limit: Optional[int] = None) -> List[Flashcard]:
        """Get cards due for review"""
        card_data_list = self.db.get_due_cards(user_id)
        cards = [Flashcard.from_dict(card_data) for card_data in card_data_list]

        # Sort by priority (overdue first, then by interval)
        cards.sort(key=lambda c: (
            c.scheduling.days_until_due(),  # Negative for overdue
            c.scheduling.interval_days      # Shorter intervals first
        ))

        return cards[:limit] if limit else cards

    def review_card(self, card_id: str, quality: int, response_time: Optional[float] = None,
                   **kwargs) -> Optional[FlashcardReview]:
        """Process a card review"""
        try:
            card = self.get_card(card_id)
            if not card:
                self.logger.error(f"Card {card_id} not found")
                return None

            # Process review
            review = card.review(quality, response_time, **kwargs)

            # Save updated card and review
            self.db.update_card(card.card_id, card.to_dict())
            self.db.save_review(review.to_dict())

            self.logger.info(f"Reviewed card {card_id}: quality={quality}, "
                           f"next_review={card.scheduling.next_review_date}")
            return review

        except Exception as e:
            self.logger.error(f"Failed to review card {card_id}: {e}")
            return None

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
        """Get comprehensive user statistics"""
        base_stats = self.db.get_user_stats(user_id)

        # Add more detailed stats
        cards = self.get_user_cards(user_id)
        due_cards = self.get_due_cards(user_id)

        # Difficulty breakdown
        difficulty_counts = {'Easy': 0, 'Medium': 0, 'Hard': 0}
        for card in cards:
            difficulty = card.get_difficulty_level()
            difficulty_counts[difficulty] += 1

        # Streak calculation
        recent_reviews = self.db.get_user_reviews(user_id, limit=10)
        current_streak = 0
        for review_data in recent_reviews:
            if review_data.get('quality', 0) >= 3:
                current_streak += 1
            else:
                break

        base_stats.update({
            'difficulty_breakdown': difficulty_counts,
            'current_streak': current_streak,
            'overdue_cards': len([c for c in due_cards if c.scheduling.days_until_due() < 0])
        })

        return base_stats

    def get_deck_stats(self, deck_id: str) -> Dict[str, Any]:
        """Get deck statistics"""
        cards = self.get_deck_cards(deck_id)
        deck = self.get_deck(deck_id)

        if not deck:
            return {}

        total_cards = len(cards)
        due_cards = [c for c in cards if c.is_due()]

        return {
            'deck_id': deck_id,
            'name': deck.name,
            'total_cards': total_cards,
            'cards_due': len(due_cards),
            'default_algorithm': deck.default_algorithm,
            'created_at': deck.created_at.isoformat(),
            'anki_synced': deck.anki_deck_name is not None
        }

    # === ANKI SYNC ===

    def sync_with_anki(self, user_id: str) -> Dict[str, Any]:
        """Sync user's flashcards with Anki"""
        if not self.anki_available:
            return {'success': False, 'error': 'Anki not available'}

        try:
            decks = self.get_user_decks(user_id)
            synced_decks = 0
            synced_cards = 0

            for deck in decks:
                if not deck.anki_deck_name:
                    # Create Anki deck
                    anki_deck_name = f"Telegram_{deck.name}"
                    if self.anki_client.create_deck(anki_deck_name):
                        deck.anki_deck_name = anki_deck_name
                        self.update_deck(deck)
                        synced_decks += 1

                # Sync cards in this deck
                cards = self.get_deck_cards(deck.deck_id)
                for card in cards:
                    if not card.anki_note_id:
                        note_id = self.anki_client.add_note(
                            deck.anki_deck_name, card.front, card.back
                        )
                        if note_id:
                            card.anki_note_id = note_id
                            self.update_card(card)
                            synced_cards += 1

            # Trigger Anki sync
            self.anki_client.sync()

            return {
                'success': True,
                'synced_decks': synced_decks,
                'synced_cards': synced_cards
            }

        except Exception as e:
            self.logger.error(f"Anki sync failed: {e}")
            return {'success': False, 'error': str(e)}

    # === UTILITIES ===

    def backup_database(self, backup_path: str) -> bool:
        """Create database backup"""
        return self.db.backup_database(backup_path)

    def get_service_info(self) -> Dict[str, Any]:
        """Get service information"""
        db_info = self.db.get_database_info()
        algorithms_info = self.get_available_algorithms()

        return {
            'flashcard_service': {
                'anki_enabled': self.anki_enabled,
                'anki_available': self.anki_available,
                'algorithms_available': list(algorithms_info.keys()),
                'database': db_info
            }
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