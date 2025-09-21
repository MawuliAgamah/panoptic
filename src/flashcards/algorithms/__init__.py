"""Spaced repetition algorithms"""

from .base import SpacedRepetitionAlgorithm, ReviewResult
from .sm2 import SM2Algorithm
from .sm15 import SM15Algorithm

# Algorithm registry for easy switching
ALGORITHMS = {
    'sm2': SM2Algorithm,
    'sm15': SM15Algorithm,
}

def get_algorithm(name: str = 'sm2') -> SpacedRepetitionAlgorithm:
    """Get algorithm instance by name"""
    if name not in ALGORITHMS:
        raise ValueError(f"Unknown algorithm: {name}. Available: {list(ALGORITHMS.keys())}")

    return ALGORITHMS[name]()

__all__ = ['SpacedRepetitionAlgorithm', 'ReviewResult', 'SM2Algorithm', 'SM15Algorithm', 'get_algorithm', 'ALGORITHMS']