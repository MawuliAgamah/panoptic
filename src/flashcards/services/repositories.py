"""Repository pattern for data access abstraction"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import Card, Deck, FlashcardReview


class CardRepository(ABC):
    """Abstract repository for card operations"""
    
    @abstractmethod
    def save(self, card: Card) -> Card:
        """Save or update card"""
        pass
    
    @abstractmethod
    def get_by_id(self, card_id: str) -> Optional[Card]:
        """Get card by ID"""
        pass
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[Card]:
        """Get all cards for user"""
        pass
    
    @abstractmethod
    def get_due_cards(self, user_id: str, limit: Optional[int] = None) -> List[Card]:
        """Get cards due for review (database-optimized)"""
        pass
    
    @abstractmethod
    def delete(self, card_id: str) -> bool:
        """Delete card"""
        pass


class DeckRepository(ABC):
    """Abstract repository for deck operations"""
    
    @abstractmethod
    def save(self, deck: Deck) -> Deck:
        pass
    
    @abstractmethod
    def get_by_id(self, deck_id: str) -> Optional[Deck]:
        pass
    
    @abstractmethod
    def get_by_user(self, user_id: str) -> List[Deck]:
        pass
    
    @abstractmethod
    def delete(self, deck_id: str) -> bool:
        pass


class ReviewRepository(ABC):
    """Abstract repository for review operations"""
    
    @abstractmethod
    def save(self, review: FlashcardReview) -> FlashcardReview:
        pass
    
    @abstractmethod
    def get_by_card(self, card_id: str) -> List[FlashcardReview]:
        pass
    
    @abstractmethod
    def get_by_user(self, user_id: str, limit: Optional[int] = None) -> List[FlashcardReview]:
        pass


# Concrete JSON implementations
class JSONCardRepository(CardRepository):
    """JSON-based card repository"""
    
    def __init__(self, json_db):
        self.db = json_db
    
    def save(self, card: Card) -> Card:
        self.db.create_card(card.to_dict())
        return card
    
    def get_by_id(self, card_id: str) -> Optional[Card]:
        card_data = self.db.get_card(card_id)
        if card_data:
            # Migrate old data format to new format
            card_data = self._migrate_card_data(card_data)
            return Card.from_dict(card_data)
        return None
    
    def get_by_user(self, user_id: str) -> List[Card]:
        card_data_list = self.db.get_user_cards(user_id)
        migrated_cards = []
        for data in card_data_list:
            # Migrate old data format to new format
            migrated_data = self._migrate_card_data(data)
            migrated_cards.append(Card.from_dict(migrated_data))
        return migrated_cards
    
    def get_due_cards(self, user_id: str, limit: Optional[int] = None) -> List[Card]:
        # This could be optimized at the database level
        card_data_list = self.db.get_due_cards(user_id, limit)
        migrated_cards = []
        for data in card_data_list:
            # Migrate old data format to new format
            migrated_data = self._migrate_card_data(data)
            migrated_cards.append(Card.from_dict(migrated_data))
        return migrated_cards
    
    def _migrate_card_data(self, card_data: dict) -> dict:
        """Migrate old card data format to new format"""
        migrated = card_data.copy()
        
        # Handle old 'card_id' field -> new 'id' field
        if 'card_id' in migrated and 'id' not in migrated:
            migrated['id'] = migrated.pop('card_id')
        
        # Handle old 'tags' field -> new 'Domains' field (capital D)
        if 'tags' in migrated and 'Domains' not in migrated:
            migrated['Domains'] = migrated.pop('tags')
        elif 'Domains' not in migrated:
            migrated['Domains'] = []
        
        # Remove old 'deck_id' field (not used in new model)
        if 'deck_id' in migrated:
            del migrated['deck_id']
        
        # Ensure required fields exist
        if 'response_time_seconds' not in migrated:
            migrated['response_time_seconds'] = None
        if 'kg_mapping' not in migrated:
            migrated['kg_mapping'] = None
        if 'anki_note_id' not in migrated:
            migrated['anki_note_id'] = None
        if 'reviewed_at' not in migrated:
            # Use created_at as fallback for reviewed_at
            migrated['reviewed_at'] = migrated.get('created_at', migrated.get('updated_at'))
        
        return migrated
    
    def delete(self, card_id: str) -> bool:
        return self.db.delete_card(card_id)


class JSONDeckRepository(DeckRepository):
    """JSON-based deck repository"""
    
    def __init__(self, json_db):
        self.db = json_db
    
    def save(self, deck: Deck) -> Deck:
        # Use the correct field name (id, not deck_id)
        if hasattr(deck, 'id') and deck.id:
            self.db.update_deck(deck.id, deck.to_dict())
        else:
            self.db.create_deck(deck.to_dict())
        return deck
    
    def get_by_id(self, deck_id: str) -> Optional[Deck]:
        deck_data = self.db.get_deck(deck_id)
        if deck_data:
            # Migrate old data format to new format
            deck_data = self._migrate_deck_data(deck_data)
            return Deck.from_dict(deck_data)
        return None
    
    def get_by_user(self, user_id: str) -> List[Deck]:
        deck_data_list = self.db.get_user_decks(user_id)
        migrated_decks = []
        for data in deck_data_list:
            # Migrate old data format to new format
            migrated_data = self._migrate_deck_data(data)
            migrated_decks.append(Deck.from_dict(migrated_data))
        return migrated_decks
    
    def _migrate_deck_data(self, deck_data: dict) -> dict:
        """Migrate old deck data format to new format"""
        migrated = deck_data.copy()
        
        # Handle old 'deck_id' field -> new 'id' field
        if 'deck_id' in migrated and 'id' not in migrated:
            migrated['id'] = migrated.pop('deck_id')
        
        # Remove old 'settings' field that doesn't exist in new model
        if 'settings' in migrated:
            del migrated['settings']
        
        # Ensure required fields exist with defaults
        if 'default_algorithm' not in migrated:
            migrated['default_algorithm'] = 'sm2'
        
        return migrated
    
    def delete(self, deck_id: str) -> bool:
        return self.db.delete_deck(deck_id)


class JSONReviewRepository(ReviewRepository):
    """JSON-based review repository"""
    
    def __init__(self, json_db):
        self.db = json_db
    
    def save(self, review: FlashcardReview) -> FlashcardReview:
        self.db.save_review(review.to_dict())
        return review
    
    def get_by_card(self, card_id: str) -> List[FlashcardReview]:
        review_data_list = self.db.get_card_reviews(card_id)
        return [FlashcardReview.from_dict(data) for data in review_data_list]
    
    def get_by_user(self, user_id: str, limit: Optional[int] = None) -> List[FlashcardReview]:
        review_data_list = self.db.get_user_reviews(user_id, limit)
        return [FlashcardReview.from_dict(data) for data in review_data_list]
