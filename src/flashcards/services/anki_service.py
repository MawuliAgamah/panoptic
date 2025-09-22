"""Dedicated Anki integration service"""

import asyncio
from typing import List, Dict, Any, Optional
import logging

from ..models import Card, Deck
from .archive.anki_connect import AnkiConnectClient, create_anki_client


class AnkiService:
    """
    Handles all Anki integration
    
    Separated from core flashcard logic for:
    - Better testability
    - Optional feature (can disable Anki)
    - Async processing
    """
    
    def __init__(self, client: Optional[AnkiConnectClient] = None):
        self.client = client or create_anki_client()
        self.logger = logging.getLogger(__name__)
        self.available = self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test if Anki is available"""
        try:
            return self.client.test_connection()
        except Exception as e:
            self.logger.warning(f"Anki not available: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Anki sync is available"""
        return self.available
    
    def sync_card(self, card: Card) -> bool:
        """Sync single card to Anki"""
        if not self.available:
            return False
        
        try:
            if not card.anki_note_id:
                note_id = self.client.add_note("Default", card.front, card.back)
                if note_id:
                    card.anki_note_id = note_id
                    return True
            return False
        except Exception as e:
            self.logger.error(f"Failed to sync card to Anki: {e}")
            return False
    
    def sync_cards(self, cards: List[Card]) -> Dict[str, Any]:
        """Sync multiple cards to Anki"""
        if not self.available:
            return {'success': False, 'error': 'Anki not available'}
        
        synced_count = 0
        failed_count = 0
        
        for card in cards:
            if self.sync_card(card):
                synced_count += 1
            else:
                failed_count += 1
        
        return {
            'success': True,
            'synced_cards': synced_count,
            'failed_cards': failed_count,
            'total_cards': len(cards)
        }
    
    def create_deck(self, deck: Deck) -> bool:
        """Create deck in Anki"""
        if not self.available:
            return False
        
        try:
            anki_deck_name = f"Flashcards_{deck.name}"
            success = self.client.create_deck(anki_deck_name)
            if success:
                deck.anki_deck_name = anki_deck_name
            return success
        except Exception as e:
            self.logger.error(f"Failed to create Anki deck: {e}")
            return False
    
    # Async methods for background processing
    
    def sync_card_async(self, card: Card):
        """Sync card to Anki in background"""
        if self.available:
            asyncio.create_task(self._sync_card_background(card))
    
    def create_deck_async(self, deck: Deck):
        """Create Anki deck in background"""
        if self.available:
            asyncio.create_task(self._create_deck_background(deck))
    
    async def _sync_card_background(self, card: Card):
        """Background card sync"""
        try:
            self.sync_card(card)
        except Exception as e:
            self.logger.error(f"Background card sync failed: {e}")
    
    async def _create_deck_background(self, deck: Deck):
        """Background deck creation"""
        try:
            self.create_deck(deck)
        except Exception as e:
            self.logger.error(f"Background deck creation failed: {e}")
