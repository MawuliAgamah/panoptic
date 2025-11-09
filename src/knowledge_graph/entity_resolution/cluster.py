from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Tuple
import hashlib

from .models import EntityMention, ResolvedEntity


def build_key(normalized_name: str, ent_type: str) -> str:
    return f"{(ent_type or '').lower()}|{normalized_name}"


def build_resolved_id(normalized_key: str) -> str:
    h = hashlib.sha1(normalized_key.encode("utf-8")).hexdigest()
    return f"res::{h[:16]}"


def block_mentions(mentions: List[Tuple[EntityMention, str]]) -> Dict[str, List[EntityMention]]:
    """Group mentions by normalized_key.

    Input is a list of (mention, normalized_key) pairs.
    """
    blocks: Dict[str, List[EntityMention]] = defaultdict(list)
    for m, key in mentions:
        blocks[key].append(m)
    return blocks


def choose_primary_name(mentions: List[EntityMention]) -> str:
    names = [m.name for m in mentions if m.name]
    if not names:
        return ""
    freq = Counter(names)
    max_count = max(freq.values())
    candidates = [n for n, c in freq.items() if c == max_count]
    # tie-breaker: longest name
    candidates.sort(key=lambda s: (-len(s), s))
    return candidates[0]


def build_resolved_entities(blocks: Dict[str, List[EntityMention]]) -> List[ResolvedEntity]:
    resolved: List[ResolvedEntity] = []
    for key, group in blocks.items():
        # type|normalized_name
        parts = key.split("|", 1)
        ent_type = parts[0] if parts else ""
        primary = choose_primary_name(group)
        category = group[0].category if group else "general"
        resolved_id = build_resolved_id(key)
        doc_count = len({m.document_id for m in group})
        resolved.append(
            ResolvedEntity(
                resolved_id=resolved_id,
                primary_name=primary,
                normalized_key=key,
                type=ent_type,
                category=category,
                mention_count=len(group),
                doc_count=doc_count,
            )
        )
    return resolved

