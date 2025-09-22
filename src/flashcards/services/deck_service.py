"""Deck management service"""

from typing import List, Optional
from ..models import Deck
from .repositories import DeckRepository
from ..config import FlashcardConfig


class DeckService:
    """
    Handles deck operations
    Single responsibility: Deck lifecycle management
    """
    
    def __init__(self, deck_repository: DeckRepository):
        self.repository = deck_repository
    
    def create_deck(self, user_id: str, name: str, description: str = "",
                   algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM) -> Deck:
        """Create a new deck"""
        deck = Deck.create_new(user_id, name, description, algorithm)
        return self.repository.save(deck)
    
    def get_deck(self, deck_id: str) -> Optional[Deck]:
        """Get deck by ID"""
        return self.repository.get_by_id(deck_id)
    
    def get_user_decks(self, user_id: str) -> List[Deck]:
        """Get all decks for user"""
        return self.repository.get_by_user(user_id)
    
    def update_deck(self, deck: Deck) -> Deck:
        """Update deck"""
        return self.repository.save(deck)
    
    def delete_deck(self, deck_id: str) -> bool:
        """Delete deck"""
        return self.repository.delete(deck_id)
