"""Flashcard models with modular spaced repetition support"""

from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import uuid
import json
from ..algorithms import get_algorithm, SpacedRepetitionAlgorithm


@dataclass
class FlashcardReview:
    """Individual review session data"""
    review_id: str
    card_id: str
    user_id: str
    quality: int  # Quality rating (scale depends on algorithm)
    response_time_seconds: Optional[float]
    reviewed_at: datetime
    ease_factor_before: float
    interval_before: int
    repetitions_before: int
    algorithm_used: str = "sm2"  # Which algorithm was used
    algorithm_metadata: Dict[str, Any] = None  # Algorithm-specific data

    def __post_init__(self):
        if self.algorithm_metadata is None:
            self.algorithm_metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['reviewed_at'] = self.reviewed_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlashcardReview':
        data = data.copy()
        data['reviewed_at'] = datetime.fromisoformat(data['reviewed_at'])
        return cls(**data)


@dataclass
class SpacedRepetitionData:
    """Spaced repetition scheduling data with algorithm support"""
    ease_factor: float = 2.5  # Default ease factor
    interval_days: int = 1    # Days until next review
    repetitions: int = 0      # Number of successful reviews
    next_review_date: Optional[datetime] = None
    last_review_date: Optional[datetime] = None
    total_reviews: int = 0
    correct_streak: int = 0
    algorithm_name: str = "sm2"  # Which algorithm to use
    difficulty: float = 0.0      # Algorithm-specific difficulty tracking
    algorithm_data: Dict[str, Any] = None  # Algorithm-specific storage

    def __post_init__(self):
        if self.algorithm_data is None:
            self.algorithm_data = {}

    def calculate_next_review(self, quality: int, algorithm: Optional[SpacedRepetitionAlgorithm] = None, **kwargs) -> Dict[str, Any]:
        """Update scheduling using specified algorithm"""
        if algorithm is None:
            algorithm = get_algorithm(self.algorithm_name)

        # Validate quality for the algorithm
        if not algorithm.validate_quality(quality):
            raise ValueError(f"Invalid quality {quality} for {algorithm.name}. "
                           f"Valid range: {list(algorithm.get_quality_scale().keys())}")

        # Get algorithm result
        result = algorithm.calculate_next_review(
            quality=quality,
            current_ease_factor=self.ease_factor,
            current_interval=self.interval_days,
            current_repetitions=self.repetitions,
            last_review_date=self.last_review_date,
            difficulty=self.difficulty,
            **kwargs
        )

        # Update our data from algorithm result
        self.last_review_date = datetime.now()
        self.total_reviews += 1
        self.ease_factor = result.ease_factor
        self.interval_days = result.next_interval_days
        self.repetitions = result.repetitions
        self.next_review_date = result.next_review_date

        # Update algorithm-specific data
        if hasattr(result, 'difficulty_adjustment'):
            self.difficulty = result.difficulty_adjustment

        # Update streak tracking
        if quality >= 3:  # Assuming 3+ means correct (varies by algorithm)
            self.correct_streak += 1
        else:
            self.correct_streak = 0

        # Store algorithm metadata
        self.algorithm_data.update(result.metadata or {})

        return {
            'result': result,
            'algorithm_name': algorithm.name,
            'quality_description': algorithm.get_quality_scale().get(quality, "Unknown"),
            'confidence': result.confidence
        }

    def is_due(self, current_time: Optional[datetime] = None) -> bool:
        """Check if card is due for review"""
        if self.next_review_date is None:
            return True  # New card, ready for first review

        current_time = current_time or datetime.now()
        return current_time >= self.next_review_date

    def days_until_due(self, current_time: Optional[datetime] = None) -> int:
        """Get days until card is due (negative = overdue)"""
        if self.next_review_date is None:
            return 0

        current_time = current_time or datetime.now()
        delta = self.next_review_date - current_time
        return delta.days

    def switch_algorithm(self, new_algorithm_name: str) -> None:
        """Switch to a different spaced repetition algorithm"""
        try:
            new_algorithm = get_algorithm(new_algorithm_name)
            self.algorithm_name = new_algorithm_name

            # Reset algorithm-specific data
            self.algorithm_data = {}

            # Adjust ease factor if needed for new algorithm
            if self.ease_factor <= 0:
                self.ease_factor = new_algorithm.get_default_ease_factor()

        except ValueError as e:
            raise ValueError(f"Cannot switch to algorithm '{new_algorithm_name}': {e}")

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about current algorithm"""
        algorithm = get_algorithm(self.algorithm_name)
        return algorithm.get_algorithm_info()

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if self.next_review_date:
            data['next_review_date'] = self.next_review_date.isoformat()
        if self.last_review_date:
            data['last_review_date'] = self.last_review_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpacedRepetitionData':
        data = data.copy()
        if data.get('next_review_date'):
            data['next_review_date'] = datetime.fromisoformat(data['next_review_date'])
        if data.get('last_review_date'):
            data['last_review_date'] = datetime.fromisoformat(data['last_review_date'])
        return cls(**data)


@dataclass
class Flashcard:
    """Individual flashcard with content and scheduling"""
    card_id: str
    deck_id: str
    user_id: str
    front: str  # Question
    back: str   # Answer
    tags: list[str]
    created_at: datetime
    updated_at: datetime
    scheduling: SpacedRepetitionData
    anki_note_id: Optional[int] = None  # For Anki sync

    def __post_init__(self):
        """Initialize scheduling if not provided"""
        if isinstance(self.scheduling, dict):
            self.scheduling = SpacedRepetitionData.from_dict(self.scheduling)

    @classmethod
    def create_new(cls, deck_id: str, user_id: str, front: str, back: str,
                   tags: list[str] = None, algorithm: str = "sm2") -> 'Flashcard':
        """Create a new flashcard with specified algorithm"""
        now = datetime.now()

        # Get algorithm to set proper defaults
        algo = get_algorithm(algorithm)

        return cls(
            card_id=str(uuid.uuid4()),
            deck_id=deck_id,
            user_id=user_id,
            front=front,
            back=back,
            tags=tags or [],
            created_at=now,
            updated_at=now,
            scheduling=SpacedRepetitionData(
                algorithm_name=algorithm,
                ease_factor=algo.get_default_ease_factor()
            )
        )

    def review(self, quality: int, response_time: Optional[float] = None, **kwargs) -> FlashcardReview:
        """Process a review and update scheduling using current algorithm"""

        # Create review record
        review = FlashcardReview(
            review_id=str(uuid.uuid4()),
            card_id=self.card_id,
            user_id=self.user_id,
            quality=quality,
            response_time_seconds=response_time,
            reviewed_at=datetime.now(),
            ease_factor_before=self.scheduling.ease_factor,
            interval_before=self.scheduling.interval_days,
            repetitions_before=self.scheduling.repetitions,
            algorithm_used=self.scheduling.algorithm_name
        )

        # Update scheduling using algorithm
        result_data = self.scheduling.calculate_next_review(
            quality=quality,
            response_time_seconds=response_time,
            **kwargs
        )

        # Store algorithm metadata in review
        review.algorithm_metadata = result_data.get('result', {}).metadata or {}

        self.updated_at = datetime.now()

        return review

    def switch_algorithm(self, new_algorithm: str) -> None:
        """Switch this card to use a different algorithm"""
        self.scheduling.switch_algorithm(new_algorithm)
        self.updated_at = datetime.now()

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the algorithm used by this card"""
        return self.scheduling.get_algorithm_info()

    def get_quality_scale(self) -> Dict[int, str]:
        """Get the quality scale for this card's algorithm"""
        algorithm = get_algorithm(self.scheduling.algorithm_name)
        return algorithm.get_quality_scale()

    def is_due(self) -> bool:
        """Check if card is due for review"""
        return self.scheduling.is_due()

    def get_difficulty_level(self) -> str:
        """Get human-readable difficulty level based on algorithm data"""
        # Try to get difficulty from algorithm-specific data first
        if self.scheduling.difficulty > 0:
            if self.scheduling.difficulty > 0.7:
                return "Hard"
            elif self.scheduling.difficulty > 0.4:
                return "Medium"
            else:
                return "Easy"

        # Fall back to ease factor for algorithms that don't use difficulty
        if self.scheduling.ease_factor > 2.8:
            return "Easy"
        elif self.scheduling.ease_factor > 2.2:
            return "Medium"
        else:
            return "Hard"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            'card_id': self.card_id,
            'deck_id': self.deck_id,
            'user_id': self.user_id,
            'front': self.front,
            'back': self.back,
            'tags': self.tags,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'scheduling': self.scheduling.to_dict(),
            'anki_note_id': self.anki_note_id
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Flashcard':
        """Create from dictionary"""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        data['scheduling'] = SpacedRepetitionData.from_dict(data['scheduling'])
        return cls(**data)


@dataclass
class Deck:
    """Flashcard deck container with algorithm preferences"""
    deck_id: str
    user_id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    settings: Dict[str, Any]  # Deck-specific settings
    default_algorithm: str = "sm2"  # Default algorithm for new cards
    anki_deck_name: Optional[str] = None  # For Anki sync

    @classmethod
    def create_new(cls, user_id: str, name: str, description: str = "",
                   default_algorithm: str = "sm2") -> 'Deck':
        """Create a new deck with specified default algorithm"""
        now = datetime.now()

        # Validate algorithm exists
        try:
            get_algorithm(default_algorithm)
        except ValueError:
            default_algorithm = "sm2"  # Fall back to SM-2

        return cls(
            deck_id=str(uuid.uuid4()),
            user_id=user_id,
            name=name,
            description=description,
            created_at=now,
            updated_at=now,
            settings={},
            default_algorithm=default_algorithm
        )

    def switch_default_algorithm(self, new_algorithm: str) -> None:
        """Change the default algorithm for new cards in this deck"""
        try:
            get_algorithm(new_algorithm)  # Validate algorithm exists
            self.default_algorithm = new_algorithm
            self.updated_at = datetime.now()
        except ValueError as e:
            raise ValueError(f"Cannot set default algorithm to '{new_algorithm}': {e}")

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about the default algorithm"""
        algorithm = get_algorithm(self.default_algorithm)
        return algorithm.get_algorithm_info()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage"""
        return {
            'deck_id': self.deck_id,
            'user_id': self.user_id,
            'name': self.name,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'settings': self.settings,
            'anki_deck_name': self.anki_deck_name
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Deck':
        """Create from dictionary"""
        data = data.copy()
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])
        return cls(**data)