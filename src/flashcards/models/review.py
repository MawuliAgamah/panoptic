"""FlashcardReview model for tracking review sessions"""

from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional, Dict, Any
from ..config import FlashcardConfig


@dataclass
class FlashcardReview:
    """Individual review session data"""
    review_id: str
    card_id: str
    user_id: str
    quality: int
    response_time_seconds: Optional[float]
    reviewed_at: datetime
    ease_factor_before: float
    interval_before: int
    repetitions_before: int
    algorithm_used: str = FlashcardConfig.DEFAULT_ALGORITHM
    algorithm_metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        if self.algorithm_metadata is None:
            self.algorithm_metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        data['reviewed_at'] = self.reviewed_at.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FlashcardReview':
        """Create from dictionary"""
        data = data.copy()
        data['reviewed_at'] = datetime.fromisoformat(data['reviewed_at'])
        return cls(**data)
