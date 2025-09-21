"""SM-2 Algorithm implementation (Anki's algorithm)"""

from datetime import datetime, timedelta
from typing import Dict, Optional
from .base import SpacedRepetitionAlgorithm, ReviewResult


class SM2Algorithm(SpacedRepetitionAlgorithm):
    """
    SuperMemo-2 Algorithm (1987)

    The classic spaced repetition algorithm used by Anki.
    Simple, proven, and well-understood.

    Quality scale: 0-5
    - 0: Complete blackout
    - 1: Incorrect, but remembered something
    - 2: Incorrect, but easy to remember correct answer
    - 3: Correct with serious difficulty
    - 4: Correct after hesitation
    - 5: Perfect recall
    """

    def __init__(self):
        super().__init__("SM-2", "1.0")

    def calculate_next_review(
        self,
        quality: int,
        current_ease_factor: float,
        current_interval: int,
        current_repetitions: int,
        last_review_date: Optional[datetime] = None,
        **kwargs
    ) -> ReviewResult:
        """Calculate next review using SM-2 algorithm"""

        if not self.validate_quality(quality):
            raise ValueError(f"Invalid quality {quality} for SM-2. Must be 0-5.")

        last_review_date = last_review_date or datetime.now()

        # Store original values for metadata
        original_ease = current_ease_factor
        original_interval = current_interval
        original_reps = current_repetitions

        # Initialize ease factor if needed
        if current_ease_factor <= 0:
            current_ease_factor = self.get_default_ease_factor()

        # SM-2 Algorithm Logic
        if quality >= 3:  # Correct answer
            if current_repetitions == 0:
                next_interval = 1
            elif current_repetitions == 1:
                next_interval = 6
            else:
                next_interval = round(current_interval * current_ease_factor)

            next_repetitions = current_repetitions + 1
        else:  # Incorrect answer
            next_repetitions = 0
            next_interval = 1

        # Update ease factor
        new_ease_factor = current_ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        new_ease_factor = max(1.3, new_ease_factor)  # Minimum ease factor

        # Calculate next review date
        next_review_date = last_review_date + timedelta(days=next_interval)

        # Create result
        result = ReviewResult(
            next_interval_days=next_interval,
            ease_factor=new_ease_factor,
            repetitions=next_repetitions,
            next_review_date=next_review_date,
            confidence=self._calculate_confidence(quality, current_repetitions),
            metadata={
                'algorithm': 'SM-2',
                'quality_description': self.get_quality_scale()[quality],
                'ease_change': new_ease_factor - original_ease,
                'interval_change': next_interval - original_interval,
                'was_correct': quality >= 3
            }
        )

        self.log_calculation(quality, result,
                           original_ease=original_ease,
                           original_interval=original_interval,
                           original_reps=original_reps)

        return result

    def get_quality_scale(self) -> Dict[int, str]:
        """SM-2 uses 0-5 quality scale"""
        return {
            0: "Complete blackout",
            1: "Incorrect, but remembered something",
            2: "Incorrect, but easy to remember correct answer",
            3: "Correct with serious difficulty",
            4: "Correct after hesitation",
            5: "Perfect recall"
        }

    def get_default_ease_factor(self) -> float:
        """SM-2 default ease factor"""
        return 2.5

    def validate_quality(self, quality: int) -> bool:
        """Validate quality is in 0-5 range"""
        return 0 <= quality <= 5

    def _calculate_confidence(self, quality: int, repetitions: int) -> float:
        """Calculate algorithm confidence in the scheduling decision"""
        base_confidence = 0.8

        # Higher quality = higher confidence
        quality_bonus = quality * 0.03

        # More repetitions = higher confidence (up to a point)
        repetition_bonus = min(repetitions * 0.02, 0.15)

        return min(1.0, base_confidence + quality_bonus + repetition_bonus)


class SM2PlusAlgorithm(SM2Algorithm):
    """
    Enhanced SM-2 with additional features
    - Difficulty adjustment based on review history
    - Minimum/maximum interval caps
    - Review time consideration
    """

    def __init__(self, min_interval: int = 1, max_interval: int = 365):
        super().__init__()
        self.name = "SM-2+"
        self.version = "1.0"
        self.min_interval = min_interval
        self.max_interval = max_interval

    def calculate_next_review(
        self,
        quality: int,
        current_ease_factor: float,
        current_interval: int,
        current_repetitions: int,
        last_review_date: Optional[datetime] = None,
        review_time_seconds: Optional[float] = None,
        recent_failure_count: int = 0,
        **kwargs
    ) -> ReviewResult:
        """Enhanced SM-2 calculation with additional factors"""

        # Get base SM-2 result
        result = super().calculate_next_review(
            quality, current_ease_factor, current_interval,
            current_repetitions, last_review_date, **kwargs
        )

        # Apply enhancements
        original_interval = result.next_interval_days

        # Adjust for recent failures
        if recent_failure_count > 0:
            failure_penalty = 0.9 ** recent_failure_count
            result.next_interval_days = max(1, round(result.next_interval_days * failure_penalty))

        # Adjust for review time (if provided)
        if review_time_seconds is not None:
            time_factor = self._get_time_factor(review_time_seconds, quality)
            result.next_interval_days = max(1, round(result.next_interval_days * time_factor))

        # Apply interval caps
        result.next_interval_days = max(self.min_interval,
                                      min(self.max_interval, result.next_interval_days))

        # Recalculate next review date if interval changed
        if result.next_interval_days != original_interval:
            last_review_date = last_review_date or datetime.now()
            result.next_review_date = last_review_date + timedelta(days=result.next_interval_days)

        # Update metadata
        result.metadata.update({
            'algorithm': 'SM-2+',
            'original_interval': original_interval,
            'interval_adjustments': {
                'failure_penalty': recent_failure_count > 0,
                'time_adjustment': review_time_seconds is not None,
                'capped': result.next_interval_days in [self.min_interval, self.max_interval]
            },
            'recent_failure_count': recent_failure_count,
            'review_time_seconds': review_time_seconds
        })

        return result

    def _get_time_factor(self, review_time_seconds: float, quality: int) -> float:
        """Calculate time-based adjustment factor"""
        # If it took a long time but got it right, maybe make interval shorter
        # If it was quick and correct, maybe make interval longer

        # Expected times for each quality level (in seconds)
        expected_times = {0: 30, 1: 25, 2: 20, 3: 15, 4: 10, 5: 5}
        expected = expected_times.get(quality, 15)

        if review_time_seconds > expected * 2:
            return 0.9  # Took too long, reduce interval
        elif review_time_seconds < expected * 0.5 and quality >= 4:
            return 1.1  # Very quick and correct, increase interval
        else:
            return 1.0  # No adjustment