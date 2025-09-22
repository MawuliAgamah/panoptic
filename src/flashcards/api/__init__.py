"""
Flashcard API - Primary interface for flashcard operations

This module provides the main FlashcardClient that users should interact with.
"""

from .client import FlashcardClient, FlashcardResult, create_flashcard_client

# Primary exports - this is what users import
__all__ = [
    'FlashcardClient',
    'FlashcardResult', 
    'create_flashcard_client'
]
