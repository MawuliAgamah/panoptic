"""SM-15 Algorithm implementation (Alternative algorithm)"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from .base import SpacedRepetitionAlgorithm, ReviewResult, ConfigurableAlgorithm
import math


class SM15Algorithm(ConfigurableAlgorithm):
    """
    SM-15 Algorithm (Simplified Version)

    A more modern approach to spaced repetition with:
    - Improved difficulty estimation
    - Better handling of forgotten items
    - More granular quality assessment

    Quality scale: 1-4
    - 1: No recall, complete failure
    - 2: Partial recall, needed help
    - 3: Correct recall with effort
    - 4: Easy, automatic recall
    """

    def __init__(self, config: Dict[str, any] = None):
        default_config = self.get_default_config()
        if config:
            default_config.update(config)

        super().__init__("SM-15", "1.0", default_config)

    def calculate_next_review(
        self,
        quality: int,
        current_ease_factor: float,
        current_interval: int,
        current_repetitions: int,
        last_review_date: Optional[datetime] = None,
        difficulty: float = 0.0,
        **kwargs
    ) -> ReviewResult:
        """Calculate next review using SM-15 algorithm"""

        if not self.validate_quality(quality):
            raise ValueError(f"Invalid quality {quality} for SM-15. Must be 1-4.")

        last_review_date = last_review_date or datetime.now()

        # Initialize values
        if current_ease_factor <= 0:
            current_ease_factor = self.get_default_ease_factor()

        if difficulty == 0.0:
            difficulty = self.config['default_difficulty']

        # Calculate difficulty change based on quality
        difficulty_change = self._calculate_difficulty_change(quality)
        new_difficulty = max(0.0, min(1.0, difficulty + difficulty_change))

        # Calculate interval based on quality and difficulty
        if quality >= 3:  # Successful recall
            if current_repetitions == 0:
                next_interval = self.config['first_interval']
            elif current_repetitions == 1:
                next_interval = self.config['second_interval']
            else:
                # Use modified ease factor based on difficulty
                adjusted_ease = current_ease_factor * (1 - new_difficulty * 0.3)
                next_interval = round(current_interval * adjusted_ease)

            next_repetitions = current_repetitions + 1
        else:  # Failed recall
            next_repetitions = 0
            # Shorter interval for failed cards, adjusted by difficulty
            failure_factor = self.config['failure_factor'] * (1 + new_difficulty * 0.5)
            next_interval = max(1, round(current_interval * failure_factor))

        # Update ease factor
        ease_change = self._calculate_ease_change(quality, new_difficulty)
        new_ease_factor = max(self.config['min_ease'],
                             min(self.config['max_ease'],
                                current_ease_factor + ease_change))

        # Apply interval bounds
        next_interval = max(self.config['min_interval'],
                           min(self.config['max_interval'], next_interval))

        # Calculate next review date
        next_review_date = last_review_date + timedelta(days=next_interval)

        # Calculate confidence based on difficulty and repetitions
        confidence = self._calculate_confidence(quality, new_difficulty, next_repetitions)

        result = ReviewResult(
            next_interval_days=next_interval,
            ease_factor=new_ease_factor,
            repetitions=next_repetitions,
            next_review_date=next_review_date,
            difficulty_adjustment=new_difficulty,
            confidence=confidence,
            metadata={
                'algorithm': 'SM-15',
                'quality_description': self.get_quality_scale()[quality],
                'difficulty': new_difficulty,
                'difficulty_change': difficulty_change,
                'ease_change': ease_change,
                'was_successful': quality >= 3,
                'config_used': self.config.copy()
            }
        )

        self.log_calculation(quality, result,
                           difficulty=new_difficulty,
                           ease_change=ease_change)

        return result

    def get_quality_scale(self) -> Dict[int, str]:
        """SM-15 uses 1-4 quality scale"""
        return {
            1: "No recall, complete failure",
            2: "Partial recall, needed help",
            3: "Correct recall with effort",
            4: "Easy, automatic recall"
        }

    def get_default_ease_factor(self) -> float:
        """SM-15 default ease factor"""
        return 2.6

    def validate_quality(self, quality: int) -> bool:
        """Validate quality is in 1-4 range"""
        return 1 <= quality <= 4

    def get_default_config(self) -> Dict[str, any]:
        """Default configuration for SM-15"""
        return {
            'first_interval': 1,
            'second_interval': 6,
            'failure_factor': 0.2,
            'min_ease': 1.3,
            'max_ease': 4.0,
            'min_interval': 1,
            'max_interval': 365,
            'default_difficulty': 0.3,
            'difficulty_decay': 0.02,
            'ease_sensitivity': 0.15
        }

    def validate_config(self, config: Dict[str, any]) -> bool:
        """Validate configuration parameters"""
        required_keys = set(self.get_default_config().keys())
        provided_keys = set(config.keys())

        # Check if all provided keys are valid
        invalid_keys = provided_keys - required_keys
        if invalid_keys:
            self.logger.error(f"Invalid config keys: {invalid_keys}")
            return False

        # Validate value ranges
        if 'min_ease' in config and 'max_ease' in config:
            if config['min_ease'] >= config['max_ease']:
                self.logger.error("min_ease must be less than max_ease")
                return False

        if 'min_interval' in config and 'max_interval' in config:
            if config['min_interval'] >= config['max_interval']:
                self.logger.error("min_interval must be less than max_interval")
                return False

        return True

    def _calculate_difficulty_change(self, quality: int) -> float:
        """Calculate how much difficulty should change based on quality"""
        # Quality 1: increase difficulty significantly
        # Quality 2: increase difficulty slightly
        # Quality 3: decrease difficulty slightly
        # Quality 4: decrease difficulty more

        quality_to_change = {
            1: 0.15,   # Big difficulty increase
            2: 0.05,   # Small difficulty increase
            3: -0.03,  # Small difficulty decrease
            4: -0.08   # Bigger difficulty decrease
        }

        return quality_to_change.get(quality, 0.0)

    def _calculate_ease_change(self, quality: int, difficulty: float) -> float:
        """Calculate ease factor change based on quality and difficulty"""
        base_changes = {
            1: -0.20,  # Significant decrease
            2: -0.05,  # Small decrease
            3: 0.00,   # No change
            4: 0.10    # Increase
        }

        base_change = base_changes.get(quality, 0.0)

        # Adjust based on difficulty
        difficulty_modifier = (0.5 - difficulty) * self.config['ease_sensitivity']

        return base_change + difficulty_modifier

    def _calculate_confidence(self, quality: int, difficulty: float, repetitions: int) -> float:
        """Calculate algorithm confidence in scheduling decision"""
        base_confidence = 0.75

        # Higher quality = higher confidence
        quality_bonus = (quality - 1) * 0.08  # 0 to 0.24

        # Lower difficulty = higher confidence
        difficulty_penalty = difficulty * 0.2

        # More repetitions = higher confidence (diminishing returns)
        repetition_bonus = min(0.15, repetitions * 0.03)

        confidence = base_confidence + quality_bonus - difficulty_penalty + repetition_bonus

        return max(0.1, min(1.0, confidence))


class ExperimentalAlgorithm(ConfigurableAlgorithm):
    """
    Experimental algorithm for testing new ideas

    This is where you can implement and test completely new approaches
    """

    def __init__(self, config: Dict[str, any] = None):
        default_config = {
            'learning_rate': 0.1,
            'memory_strength_decay': 0.95,
            'success_bonus': 1.2,
            'failure_penalty': 0.5
        }

        if config:
            default_config.update(config)

        super().__init__("Experimental", "0.1", default_config)

    def calculate_next_review(self, quality: int, current_ease_factor: float,
                            current_interval: int, current_repetitions: int,
                            last_review_date: Optional[datetime] = None,
                            **kwargs) -> ReviewResult:
        """Experimental calculation - implement your ideas here!"""

        # This is where you can experiment with completely new approaches
        # For now, it's a placeholder that falls back to SM-2 logic

        last_review_date = last_review_date or datetime.now()

        # Your experimental logic goes here
        # For example: neural network-based scheduling, genetic algorithms,
        # reinforcement learning approaches, etc.

        # Placeholder implementation
        next_interval = max(1, current_interval * (1.5 if quality >= 3 else 0.5))
        next_review_date = last_review_date + timedelta(days=next_interval)

        return ReviewResult(
            next_interval_days=next_interval,
            ease_factor=current_ease_factor,
            repetitions=current_repetitions + (1 if quality >= 3 else 0),
            next_review_date=next_review_date,
            metadata={'algorithm': 'Experimental', 'note': 'This is a placeholder'}
        )

    def get_quality_scale(self) -> Dict[int, str]:
        return {1: "Failed", 2: "Hard", 3: "Good", 4: "Easy"}

    def get_default_ease_factor(self) -> float:
        return 2.5

    def validate_quality(self, quality: int) -> bool:
        return 1 <= quality <= 4

    def get_default_config(self) -> Dict[str, any]:
        return self.config

    def validate_config(self, config: Dict[str, any]) -> bool:
        return True  # Accept any config for experimental purposes