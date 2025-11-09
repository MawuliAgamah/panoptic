from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import uuid


class KnowledgeBase(BaseModel):
    """Represents a user-owned knowledge base namespace.

    Fields are JSON-serializable for lightweight persistence. The `slug` is a
    normalized, URL-safe identifier derived from the name and used for lookups.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    slug: str
    owner_id: Optional[str] = None
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

