from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union
import uuid
import json
from ..algorithms import get_algorithm, SpacedRepetitionAlgorithm
from .KG_Mapping import KG_Mapping
from ..config import FlashcardConfig


@dataclass
class SpacedRepetitionData:
    """Spaced repetition scheduling data"""
    algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM
    ease_factor: float = FlashcardConfig.SM2_DEFAULT_EASE_FACTOR
    interval_days: int = FlashcardConfig.SM2_MIN_INTERVAL_DAYS
    repetitions: int = 0
    next_review_date: Optional[datetime] = None
    last_review_date: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        data = asdict(self)
        if self.next_review_date:
            data['next_review_date'] = self.next_review_date.isoformat()
        if self.last_review_date:
            data['last_review_date'] = self.last_review_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SpacedRepetitionData':
        """Create from dictionary"""
        data = data.copy()
        
        # Handle old fields (not used in new model)
        old_fields = ['total_reviews', 'correct_streak', 'algorithm_name', 'difficulty', 'algorithm_data']
        for field in old_fields:
            if field in data:
                del data[field]
        
        # Handle datetime fields
        if data.get('next_review_date'):
            data['next_review_date'] = datetime.fromisoformat(data['next_review_date'])
        if data.get('last_review_date'):
            data['last_review_date'] = datetime.fromisoformat(data['last_review_date'])
        
        return cls(**data)



@dataclass
class Card:
    # Required fields (no defaults)
    id: str
    user_id: str
    front: str
    back: str   
    Domains: list[str]
    scheduling: SpacedRepetitionData
    created_at: datetime
    updated_at: datetime
    reviewed_at: datetime
    
    # Optional fields (with defaults)
    response_time_seconds: Optional[float] = None
    kg_mapping: Optional[KG_Mapping] = None  # Knowledge graph mapping
    anki_note_id: Optional[int] = None  # For Anki sync


    def __repr__(self):
        return f"Card(id={self.id}, front='{self.front[:30]}...', user_id={self.user_id})"

    @classmethod 
    def create_new(cls, user_id: str, front: str, back: str, domains: list[str] = None,
                   algorithm: str = FlashcardConfig.DEFAULT_ALGORITHM, kg_mapping: Optional[KG_Mapping] = None) -> 'Card':
        """Create a new card with default values"""
        now = datetime.now()
        
        if domains is None:
            domains = []
            
        # Initialize spaced repetition data
        algo = get_algorithm(algorithm)
        scheduling = SpacedRepetitionData(
            algorithm=algorithm,
            ease_factor=algo.get_default_ease_factor(),
            interval_days=1,
            repetitions=0,
            next_review_date=now,
            last_review_date=None
        )
        
        return cls(
            id=str(uuid.uuid4()),
            user_id=user_id,
            front=front,
            back=back,
            Domains=domains,
            scheduling=scheduling,
            created_at=now,
            updated_at=now,
            reviewed_at=now,
            response_time_seconds=None,
            kg_mapping=kg_mapping,
            anki_note_id=None
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Card':
        """Create Card instance from dictionary"""
        data = data.copy()  # Don't modify original
        
        # Handle datetime fields
        datetime_fields = ['created_at', 'updated_at', 'reviewed_at']
        for field in datetime_fields:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Handle complex nested objects
        if 'scheduling' in data:
            data['scheduling'] = SpacedRepetitionData.from_dict(data['scheduling'])
        
        if data.get('kg_mapping'):
            data['kg_mapping'] = KG_Mapping.from_dict(data['kg_mapping'])
        
        return cls(**data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert Card instance to dictionary"""
        data = asdict(self)
        
        # Convert datetime fields to ISO format strings
        datetime_fields = ['created_at', 'updated_at', 'reviewed_at']
        for field in datetime_fields:
            if hasattr(self, field) and getattr(self, field):
                data[field] = getattr(self, field).isoformat()
        
        # Convert complex objects to dictionaries
        if self.scheduling:
            data['scheduling'] = self.scheduling.to_dict()
        
        if self.kg_mapping:
            data['kg_mapping'] = self.kg_mapping.to_dict()
            
        return data

    def update_from_review_result(self, review_result, response_time: Optional[float] = None):
        """Update card data from algorithm review result (data update only)"""
        now = datetime.now()
        
        # Update scheduling data
        self.scheduling.ease_factor = review_result.ease_factor
        self.scheduling.interval_days = review_result.next_interval_days
        self.scheduling.repetitions = review_result.repetitions
        self.scheduling.next_review_date = review_result.next_review_date
        self.scheduling.last_review_date = now
        
        # Update card timestamps
        self.updated_at = now
        self.reviewed_at = now
        self.response_time_seconds = response_time

    def is_due(self) -> bool:
        """Check if card is due for review"""
        if not self.scheduling.next_review_date:
            return True
        return datetime.now() >= self.scheduling.next_review_date


