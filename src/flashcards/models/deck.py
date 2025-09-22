"""Deck model for organizing flashcards"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
import uuid
from ..config import FlashcardConfig


@dataclass
class Deck:
    """Flashcard deck for organizing cards"""
    id: str
    user_id: str
    name: str
    description: str = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    default_algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM
    anki_deck_name: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()

    @classmethod
    def create_new(cls, user_id: str, name: str, description: str = "",
                   algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM) -> 'Deck':
        """Create a new deck with generated ID"""
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            default_algorithm=algorithm
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        if self.created_at:
            data['created_at'] = self.created_at.isoformat()
        if self.updated_at:
            data['updated_at'] = self.updated_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Deck':
        """Create from dictionary"""
        data = data.copy()
        if data.get('created_at'):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if data.get('updated_at'):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)
