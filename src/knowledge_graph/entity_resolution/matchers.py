from __future__ import annotations

from typing import List, Tuple

from .models import EntityMention
from .normalize import normalize_name
from .cluster import build_key


class ExactNormalizedMatcher:
    """Compute normalized keys for mentions using string normalization.

    Produces a list of (mention, normalized_key) tuples.
    """

    def __init__(self) -> None:
        pass

    def transform(self, mentions: List[EntityMention]) -> List[Tuple[EntityMention, str]]:
        pairs: List[Tuple[EntityMention, str]] = []
        for m in mentions:
            norm = normalize_name(m.name, m.type)
            key = build_key(norm, m.type)
            pairs.append((m, key))
        return pairs


# Placeholders for future matchers
class FuzzyTokenMatcher:
    pass


class EmbeddingMatcher:
    pass

