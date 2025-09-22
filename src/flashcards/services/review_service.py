"""Review service - handles spaced repetition algorithm logic"""

from typing import Optional
from datetime import datetime
import uuid
import logging

from ..models import Card, FlashcardReview
from ..algorithms import get_algorithm


class ReviewService:
    """
    Handles review logic and algorithm execution
    
    Separates business logic from data models.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def process_review(self, card: Card, quality: int, 
                      response_time: Optional[float] = None, **kwargs) -> FlashcardReview:
        """
        Process a card review using the appropriate algorithm
        
        Args:
            card: Card being reviewed
            quality: Review quality rating (scale depends on algorithm)
            response_time: Time taken to answer (optional)
            **kwargs: Additional algorithm-specific parameters
            
        Returns:
            FlashcardReview: Review record with all details
        """
        now = datetime.now()
        
        # Create review record BEFORE processing
        review = FlashcardReview(
            review_id=str(uuid.uuid4()),
            card_id=card.id,
            user_id=card.user_id,
            quality=quality,
            response_time_seconds=response_time,
            reviewed_at=now,
            ease_factor_before=card.scheduling.ease_factor,
            interval_before=card.scheduling.interval_days,
            repetitions_before=card.scheduling.repetitions,
            algorithm_used=card.scheduling.algorithm
        )
        
        # Get algorithm and calculate next review
        algorithm = get_algorithm(card.scheduling.algorithm)
        
        result = algorithm.calculate_next_review(
            quality=quality,
            current_ease_factor=card.scheduling.ease_factor,
            current_interval=card.scheduling.interval_days,
            current_repetitions=card.scheduling.repetitions,
            last_review_date=card.scheduling.last_review_date,
            **kwargs
        )
        
        # Update card with results (Card only handles data updates)
        card.update_from_review_result(result, response_time)
        
        self.logger.debug(f"Reviewed card {card.id}: quality={quality}, "
                         f"next_review={card.scheduling.next_review_date}")
        
        return review
    
    def get_algorithm_info(self, algorithm_name: str) -> dict:
        """Get information about a specific algorithm"""
        try:
            algorithm = get_algorithm(algorithm_name)
            return algorithm.get_algorithm_info()
        except ValueError:
            return {}
    
    def validate_quality_score(self, algorithm_name: str, quality: int) -> bool:
        """Validate quality score for given algorithm"""
        try:
            algorithm = get_algorithm(algorithm_name)
            return algorithm.validate_quality(quality)
        except ValueError:
            return False
