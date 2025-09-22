"""Core card operations service"""

from typing import List, Optional
from ..models import Card
from .repositories import CardRepository
from ..config import FlashcardConfig


class CardService:
    """
    Handles core card CRUD operations
    Single responsibility: Card lifecycle management
    """
    
    def __init__(self, card_repository: CardRepository):
        self.repository = card_repository
    
    def create_card(self, user_id: str, front: str, back: str, 
                   domains: List[str] = None, algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM) -> Card:
        """Create a new card"""
        card = Card.create_new(user_id, front, back, domains, algorithm)
        return self.repository.save(card)
    
    def get_card(self, card_id: str) -> Optional[Card]:
        """Get card by ID"""
        return self.repository.get_by_id(card_id)
    
    def update_card(self, card: Card) -> Card:
        """Update existing card"""
        return self.repository.save(card)
    
    def delete_card(self, card_id: str) -> bool:
        """Delete card"""
        return self.repository.delete(card_id)
    
    def get_user_cards(self, user_id: str) -> List[Card]:
        """Get all cards for user"""
        return self.repository.get_by_user(user_id)
    
    def get_due_cards(self, user_id: str, limit: Optional[int] = None) -> List[Card]:
        """Get cards due for review (efficient database query)"""
        return self.repository.get_due_cards(user_id, limit)
