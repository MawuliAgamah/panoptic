from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict, TypedDict


class ResolutionFilter(TypedDict, total=False):
    doc_ids: List[str]
    start_at: str
    end_at: str
    tags: List[str]


@dataclass
class EntityMention:
    entity_id: str
    name: str
    type: str
    category: str
    document_id: str
    chunk_id: Optional[int]
    created_at: Optional[str] = None


@dataclass
class ResolvedEntity:
    resolved_id: str
    primary_name: str
    normalized_key: str
    type: str
    category: str
    mention_count: int
    doc_count: int


@dataclass
class ResolvedRelation:
    resolved_rel_id: str
    subject_resolved_id: str
    predicate: str
    object_resolved_id: str
    weight: int = 0
    doc_count: int = 0
    first_seen_at: Optional[str] = None
    last_seen_at: Optional[str] = None


@dataclass
class ResolutionStats:
    mentions_loaded: int = 0
    blocks: int = 0
    resolved_entities_upserted: int = 0
    mapped_mentions: int = 0
    edges_upserted: int = 0
    rel_mentions_inserted: int = 0
    doc_count: int = 0

