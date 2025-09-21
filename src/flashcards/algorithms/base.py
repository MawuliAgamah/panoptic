"""Base classes for spaced repetition algorithms"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging


@dataclass
class ReviewResult:
    """Result of processing a review"""
    next_interval_days: int
    ease_factor: float
    repetitions: int
    next_review_date: datetime
    difficulty_adjustment: float = 0.0  # For algorithms that track difficulty
    confidence: float = 1.0  # Algorithm confidence in scheduling
    metadata: Dict[str, Any] = None  # Algorithm-specific data

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class SpacedRepetitionAlgorithm(ABC):
    """Base class for spaced repetition algorithms"""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version
        self.logger = logging.getLogger(f"algorithms.{name}")

    @abstractmethod
    def calculate_next_review(
        self,
        quality: int,
        current_ease_factor: float,
        current_interval: int,
        current_repetitions: int,
        last_review_date: Optional[datetime] = None,
        **kwargs
    ) -> ReviewResult:
        """
        Calculate next review based on performance

        Args:
            quality: Performance rating (algorithm-specific scale)
            current_ease_factor: Current ease factor
            current_interval: Current interval in days
            current_repetitions: Number of successful repetitions
            last_review_date: When last reviewed (defaults to now)
            **kwargs: Algorithm-specific parameters

        Returns:
            ReviewResult with updated scheduling parameters
        """
        pass

    @abstractmethod
    def get_quality_scale(self) -> Dict[int, str]:
        """Get the quality rating scale for this algorithm"""
        pass

    @abstractmethod
    def get_default_ease_factor(self) -> float:
        """Get the default ease factor for new cards"""
        pass

    @abstractmethod
    def validate_quality(self, quality: int) -> bool:
        """Validate if quality rating is valid for this algorithm"""
        pass

    def get_algorithm_info(self) -> Dict[str, Any]:
        """Get information about this algorithm"""
        return {
            'name': self.name,
            'version': self.version,
            'quality_scale': self.get_quality_scale(),
            'default_ease_factor': self.get_default_ease_factor(),
            'description': self.__doc__ or "No description available"
        }

    def log_calculation(self, quality: int, result: ReviewResult, **kwargs):
        """Log calculation details for debugging"""
        self.logger.debug(
            f"Algorithm: {self.name} | Quality: {quality} | "
            f"Next interval: {result.next_interval_days} days | "
            f"Ease factor: {result.ease_factor:.2f} | "
            f"Repetitions: {result.repetitions}"
        )


class AdaptiveAlgorithm(SpacedRepetitionAlgorithm):
    """Base for algorithms that adapt based on user performance history"""

    @abstractmethod
    def update_user_profile(self, user_id: str, review_history: list) -> None:
        """Update user-specific algorithm parameters"""
        pass

    @abstractmethod
    def get_user_difficulty_bias(self, user_id: str) -> float:
        """Get user's difficulty bias for personalization"""
        pass


class ConfigurableAlgorithm(SpacedRepetitionAlgorithm):
    """Base for algorithms with configurable parameters"""

    def __init__(self, name: str, version: str, config: Dict[str, Any] = None):
        super().__init__(name, version)
        self.config = config or {}

    @abstractmethod
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration parameters"""
        pass

    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration parameters"""
        pass

    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update algorithm configuration"""
        if self.validate_config(new_config):
            self.config.update(new_config)
            self.logger.info(f"Updated {self.name} config: {new_config}")
        else:
            raise ValueError(f"Invalid config for {self.name}: {new_config}")


class AlgorithmPerformanceTracker:
    """Track algorithm performance for comparison"""

    def __init__(self):
        self.algorithm_stats = {}

    def record_prediction(self, algorithm_name: str, predicted_interval: int,
                         actual_quality: int, review_date: datetime):
        """Record algorithm prediction vs actual performance"""
        if algorithm_name not in self.algorithm_stats:
            self.algorithm_stats[algorithm_name] = {
                'predictions': [],
                'accuracy_score': 0.0,
                'total_predictions': 0
            }

        self.algorithm_stats[algorithm_name]['predictions'].append({
            'predicted_interval': predicted_interval,
            'actual_quality': actual_quality,
            'review_date': review_date
        })
        self.algorithm_stats[algorithm_name]['total_predictions'] += 1

    def get_algorithm_accuracy(self, algorithm_name: str) -> float:
        """Get accuracy score for an algorithm"""
        if algorithm_name not in self.algorithm_stats:
            return 0.0

        # Implement accuracy calculation based on predictions vs actual performance
        # This is a simplified version - you can make it more sophisticated
        predictions = self.algorithm_stats[algorithm_name]['predictions']
        if not predictions:
            return 0.0

        correct_predictions = 0
        for pred in predictions[-100:]:  # Last 100 predictions
            # Consider prediction correct if quality >= 3 and interval was reasonable
            if pred['actual_quality'] >= 3:
                correct_predictions += 1

        return correct_predictions / min(len(predictions), 100)