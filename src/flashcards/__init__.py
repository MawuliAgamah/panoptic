"""Flashcard system for spaced repetition learning"""

# Primary API interface - this is the main interface users should use
from .api import FlashcardClient, FlashcardResult, create_flashcard_client

# Models (for advanced usage)
from .models import Card, SpacedRepetitionData, Deck, FlashcardReview

# Algorithms (for configuration)
from .algorithms import get_algorithm, ALGORITHMS

# Legacy service (deprecated - use FlashcardClient instead)
FlashcardService = None
create_flashcard_service = None

# Main interface - this is what you import into your main file
__all__ = [
    # PRIMARY API (recommended)
    'FlashcardClient',
    'FlashcardResult', 
    'create_flashcard_client',
    
    # Models
    'Card',
    'Deck',
    'FlashcardReview',
    'SpacedRepetitionData',
    
    # Algorithms
    'get_algorithm',
    'ALGORITHMS',
    
    # Legacy (deprecated)
    'FlashcardService',
    'create_flashcard_service',
]