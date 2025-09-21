"""Flashcard system for spaced repetition learning"""

from .services.flashcard_service import FlashcardService, create_flashcard_service
from .models import Flashcard, Deck, FlashcardReview, SpacedRepetitionData
from .algorithms import get_algorithm, ALGORITHMS

# Main interface - this is what you import into your main file
__all__ = [
    'FlashcardService',
    'create_flashcard_service',
    'Flashcard',
    'Deck',
    'FlashcardReview',
    'SpacedRepetitionData',
    'get_algorithm',
    'ALGORITHMS'
]